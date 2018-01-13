import random
import typing as tp

import aiopg.sa
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as postgresql
import sqlalchemy.engine.base
import sqlalchemy.exc as sa_exc
from aiopg.sa import result as aiopg_result
from psycopg2 import errorcodes

from pymash import loggers
from pymash import models
from pymash import parser
from pymash import tables
from pymash import utils
from pymash.tables import *

AsyncEngine = aiopg.sa.Engine
Engine = sqlalchemy.engine.base.Engine


class BaseError(Exception):
    pass


class NotFound(BaseError):
    pass


class GameResultChanged(BaseError):
    pass


@utils.log_time(loggers.web)
async def find_active_repos_order_by_rating(engine: AsyncEngine) -> tp.List[models.Repo]:
    repos = []
    async with engine.acquire() as conn:
        query = Repos.select().where(Repos.c.is_active.is_(True)).order_by(Repos.c.rating.desc())
        async for a_row in conn.execute(query):
            repos.append(make_repo_from_db_row(a_row))
    return repos


@utils.log_time(loggers.loader)
def find_all_repos(engine: Engine) -> tp.List[models.Repo]:
    with engine.connect() as conn:
        rows = conn.execute(Repos.select())
        return list(map(make_repo_from_db_row, rows))


@utils.log_time(loggers.loader)
def deactivate_repos(engine: Engine, repos: tp.List[models.Repo]) -> None:
    with engine.connect() as conn:
        repo_ids = [
            a_repo.repo_id
            for a_repo in repos
        ]
        repos_update = {
            Repos.c.is_active.key: False,
        }
        functions_update = {
            Functions.c.is_active.key: False,
        }
        conn.execute(Repos.update().where(Repos.c.repo_id.in_(repo_ids)).values(repos_update))
        conn.execute(Functions.update().where(Functions.c.repo_id.in_(repo_ids)).values(functions_update))


def make_repo_from_db_row(row: aiopg_result.RowProxy) -> models.Repo:
    return models.Repo(
        repo_id=row[Repos.c.repo_id],
        github_id=row[Repos.c.github_id],
        name=row[Repos.c.name],
        url=row[Repos.c.url],
        is_active=row[Repos.c.is_active],
        rating=row[Repos.c.rating])


@utils.log_time(loggers.web)
async def try_to_find_two_random_functions(engine: AsyncEngine) -> tp.List[models.Function]:
    select_some_function = _make_query_to_find_random_function()
    select_another_function = _make_query_to_find_random_function()
    select_two_functions = select_some_function.union_all(select_another_function)
    async with engine.acquire() as conn:
        rows = await conn.execute(select_two_functions)
    return list(map(make_function_from_db_row, rows))


@utils.log_time(loggers.games_queue)
def find_many_functions_by_ids(engine: Engine, function_ids: tp.List[int]) -> tp.List[models.Function]:
    rows = _find_many_by_ids(
        engine=engine,
        table=Functions,
        ids=function_ids)
    return list(map(make_function_from_db_row, rows))


@utils.log_time(loggers.games_queue)
def find_many_repos_by_ids(engine: Engine, repo_ids) -> tp.List[models.Repo]:
    rows = _find_many_by_ids(
        engine=engine,
        table=Repos,
        ids=repo_ids)
    return list(map(make_repo_from_db_row, rows))


@utils.log_time(loggers.games_queue)
def find_game_by_id(engine: Engine, game_id: str) -> models.Game:
    rows = _find_many_by_ids(
        engine=engine,
        table=Games,
        ids=[game_id])
    if len(rows) != 1:
        raise NotFound(f'game {game_id} not found')
    return _make_game_from_db_row(rows[0])


@utils.log_time(loggers.games_queue)
def save_game_and_match(engine: Engine, game: models.Game, match: models.Match) -> None:
    # TODO: check that doing execution_options doesn't permanently change connection when it will be returned to pool
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        try:
            _insert_game_and_change_repo_ratings(conn, game, match)
        except sa_exc.IntegrityError as exc:
            assert Games.c.game_id.name in exc.params
            assert exc.orig.pgcode == errorcodes.UNIQUE_VIOLATION
            game_from_db = find_game_by_id(engine, game.game_id)
            if game_from_db.result != game.result:
                raise GameResultChanged


@utils.log_time(loggers.loader, lambda engine, github_repo: f'{github_repo.url}')
def save_github_repo(engine: Engine, github_repo: models.GithubRepo) -> models.Repo:
    with engine.connect() as conn:
        insert_data = {
            Repos.c.github_id: github_repo.github_id,
            Repos.c.name: github_repo.name,
            Repos.c.url: github_repo.url,
            Repos.c.is_active: True,
            Repos.c.rating: models.Repo.DEFAULT_RATING,
        }
        update_data = {
            Repos.c.name.key: github_repo.name,
            Repos.c.url.key: github_repo.url,
            Repos.c.is_active.key: True,
        }
        query = postgresql.insert(Repos).values(insert_data).on_conflict_do_update(
            index_elements=[Repos.c.github_id], set_=update_data).returning(*Repos.columns)
        return make_repo_from_db_row(conn.execute(query).first())


@utils.log_time(loggers.loader, lambda engine, repo, functions: f'{len(functions)} from {repo.url}')
def update_functions(engine: Engine, repo: models.Repo, functions: tp.List[parser.Function]) -> None:
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(Functions.update().where(Functions.c.repo_id == repo.repo_id).values(
                {Functions.c.is_active.key: False}
            ))
            for a_function in functions:
                insert_data = {
                    Functions.c.repo_id: repo.repo_id,
                    Functions.c.text: a_function.text,
                    Functions.c.is_active: True,
                }
                update_data = {
                    Functions.c.is_active.key: True,
                }
                statement = postgresql.insert(Functions).values(insert_data).on_conflict_do_update(
                    index_elements=tables.repo_id_md5_text_unique_idx.expressions,
                    set_=update_data
                )
                conn.execute(statement)


@utils.log_time(loggers.games_queue)
def _insert_game_and_change_repo_ratings(conn, game: models.Game, match: models.Match) -> None:
    with conn.begin():
        conn.execute(Games.insert().values({
            Games.c.game_id: game.game_id,
            Games.c.white_id: game.white_id,
            Games.c.black_id: game.black_id,
            Games.c.white_score: game.result.white_score,
            Games.c.black_score: game.result.black_score,
        }))
        conn.execute(_make_query_to_update_rating(match.white))
        conn.execute(_make_query_to_update_rating(match.black))


def _find_many_by_ids(engine, table, ids):
    id_column = _get_id_column(table)
    with engine.connect() as conn:
        rows = list(conn.execute(table.select().where(id_column.in_(ids))))
    if len(rows) != len(ids):
        row_ids = [a_row[id_column] for a_row in rows]
        not_found_ids = set(ids) - set(row_ids)
        msg = f'ids {not_found_ids} does not exist in {table.name}'
        raise NotFound(msg)
    return rows


def _get_id_column(table):
    pkey_columns = list(table.primary_key.columns)
    assert len(pkey_columns) == 1
    return pkey_columns[0]


def _make_query_to_update_rating(repo: models.Repo):
    return Repos.update().where(Repos.c.repo_id == repo.repo_id).values(
        {Repos.c.rating: repo.rating})


def _make_query_to_find_random_function():
    x = random.random()
    select_max_random = Functions.select().with_only_columns(
        [sa.func.max(Functions.c.random)]).as_scalar()
    gte_than_random = Functions.c.random >= sa.func.least(x, select_max_random)
    is_active = Functions.c.is_active.is_(True)
    result = Functions.select().where(sa.and_(gte_than_random, is_active)).order_by(Functions.c.random).limit(1)
    return result


def make_function_from_db_row(row: dict) -> models.Function:
    return models.Function(
        function_id=row[Functions.c.function_id],
        repo_id=row[Functions.c.repo_id],
        is_active=row[Functions.c.is_active],
        text=row[Functions.c.text])


def _make_game_from_db_row(row: dict) -> models.Game:
    game_result = models.GameResult(
        white_score=row[Games.c.white_score],
        black_score=row[Games.c.black_score])
    return models.Game(
        game_id=row[Games.c.game_id],
        white_id=row[Games.c.white_id],
        black_id=row[Games.c.black_id],
        result=game_result)
