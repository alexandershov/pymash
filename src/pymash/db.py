import random

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as postgresql
import sqlalchemy.exc as sa_exc
from psycopg2 import errorcodes

from pymash import loggers
from pymash import models
from pymash import parser
from pymash import tables
from pymash import type_aliases as ta
from pymash import utils
from pymash.tables import *


class BaseError(Exception):
    pass


class NotFound(BaseError):
    pass


class GameResultChanged(BaseError):
    pass


@utils.log_time(loggers.web)
async def find_active_repos_order_by_rating(engine: ta.AsyncEngine) -> ta.Repos:
    repos = []
    repo_is_active = Repos.c.is_active.is_(True)
    query = Repos.select().where(repo_is_active).order_by(Repos.c.rating.desc())
    async with engine.acquire() as conn:
        async for a_row in conn.execute(query):
            repos.append(make_repo_from_db_row(a_row))
    return repos


@utils.log_time(loggers.loader)
def deactivate_all_other_repos(engine: ta.Engine, repos: ta.Repos) -> None:
    repo_ids = [a_repo.repo_id for a_repo in repos]

    with engine.begin() as conn:
        repos_result = _deactivate_other_only_repos(conn, repo_ids)
        functions_result = _deactivate_other_only_functions(conn, repo_ids)
    loggers.loader.info('deactivated %d repos and %d functions',
                        repos_result.rowcount, functions_result.rowcount)


def make_repo_from_db_row(row: dict) -> models.Repo:
    return models.Repo(
        repo_id=row[Repos.c.repo_id],
        github_id=row[Repos.c.github_id],
        name=row[Repos.c.name],
        url=row[Repos.c.url],
        is_active=row[Repos.c.is_active],
        rating=row[Repos.c.rating])


def make_function_from_db_row(row: dict) -> models.Function:
    return models.Function(
        function_id=row[Functions.c.function_id],
        repo_id=row[Functions.c.repo_id],
        is_active=row[Functions.c.is_active],
        text=row[Functions.c.text])


@utils.log_time(loggers.web)
async def try_to_find_two_random_functions(engine: ta.AsyncEngine) -> ta.Functions:
    select_some_function = _make_query_to_find_random_function()
    select_another_function = _make_query_to_find_random_function()
    select_two_functions = select_some_function.union_all(select_another_function)
    async with engine.acquire() as conn:
        rows = await conn.execute(select_two_functions)
        return list(map(make_function_from_db_row, rows))


@utils.log_time(loggers.games_queue)
def find_many_repos_by_function_ids(engine, white_fn_id: int, black_fn_id: int) -> ta.Repos:
    with engine.connect() as conn:
        white_fn, black_fn = _find_many_functions_by_ids(
            conn, [white_fn_id, black_fn_id])
        white_repo, black_repo = _find_many_repos_by_ids(
            conn, [white_fn.repo_id, black_fn.repo_id])
    return [white_repo, black_repo]


@utils.log_time(loggers.games_queue)
def _find_many_functions_by_ids(conn, function_ids: ta.Integers) -> ta.Functions:
    rows = _find_many_by_ids(
        conn=conn,
        table=Functions,
        ids=function_ids)
    return list(map(make_function_from_db_row, rows))


@utils.log_time(loggers.games_queue)
def _find_many_repos_by_ids(conn, repo_ids: ta.Integers) -> ta.Repos:
    rows = _find_many_by_ids(
        conn=conn,
        table=Repos,
        ids=repo_ids)
    return list(map(make_repo_from_db_row, rows))


@utils.log_time(loggers.games_queue)
def find_game_by_id(engine: ta.Engine, game_id: str) -> models.Game:
    with engine.connect() as conn:
        rows = _find_many_by_ids(
            conn=conn,
            table=Games,
            ids=[game_id])
    if len(rows) != 1:
        raise NotFound(f'game {game_id} not found in the database')
    return _make_game_from_db_row(rows[0])


@utils.log_time(loggers.games_queue)
def save_game_and_match(engine: ta.Engine, game: models.Game, match: models.Match) -> None:
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        try:
            _insert_game_and_change_repo_ratings(conn, game, match)
        except sa_exc.IntegrityError as exc:
            assert Games.c.game_id.name in exc.params
            assert exc.orig.pgcode == errorcodes.UNIQUE_VIOLATION
            game_from_db = find_game_by_id(engine, game.game_id)
            if game_from_db.result != game.result:
                raise GameResultChanged


@utils.log_time(loggers.loader, lambda engine, github_repo, functions: f'{github_repo.url}')
def upsert_repo(
        engine: ta.Engine,
        github_repo: models.GithubRepo, functions: ta.ParserFunctions) -> models.Repo:
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
    with engine.begin() as conn:
        repo = make_repo_from_db_row(conn.execute(query).first())
        _update_functions(conn, repo, functions)
        return repo


@utils.log_time(loggers.loader,
                lambda engine, repo, functions: f'{len(functions)} from {repo.url}')
def _update_functions(conn, repo: models.Repo, functions: ta.ParserFunctions) -> None:
    _deactivate_functions(conn, repo)
    _upsert_active_functions(conn, repo, functions)


def _upsert_active_functions(conn, repo: models.Repo, functions: ta.ParserFunctions):
    for fn in functions:
        _upsert_one_active_function(conn, repo, fn)


def _upsert_one_active_function(conn, repo, fn: parser.Function) -> None:
    insert_data = {
        Functions.c.repo_id: repo.repo_id,
        Functions.c.text: fn.text,
        Functions.c.is_active: True,
        Functions.c.file_name: fn.file_name,
        Functions.c.line_number: fn.line_number,
    }
    update_data = {
        Functions.c.is_active.key: True,
        Functions.c.file_name.key: fn.file_name,
        Functions.c.line_number.key: fn.line_number,
    }
    index = tables.get_index_by_name(Functions, 'functions_repo_id_md5_text_unique_idx')
    statement = postgresql.insert(Functions).values(insert_data).on_conflict_do_update(
        index_elements=index.expressions,
        set_=update_data)
    conn.execute(statement)


def _deactivate_functions(conn, repo):
    update_data = {
        Functions.c.is_active.key: False,
    }
    query = Functions.update().where(Functions.c.repo_id == repo.repo_id).values(update_data)
    conn.execute(query)


def _deactivate_other_only_repos(conn, repo_ids):
    is_other_repo = sa.not_(Repos.c.repo_id.in_(repo_ids))
    repos_update = {
        Repos.c.is_active.key: False,
    }
    return conn.execute(Repos.update().where(is_other_repo).values(repos_update))


def _deactivate_other_only_functions(conn, repo_ids):
    functions_update = {
        Functions.c.is_active.key: False,
    }
    is_other_function = sa.not_(Functions.c.repo_id.in_(repo_ids))
    return conn.execute(Functions.update().where(is_other_function).values(functions_update))


@utils.log_time(loggers.games_queue)
def _insert_game_and_change_repo_ratings(conn, game: models.Game, match: models.Match) -> None:
    insert_game = Games.insert().values({
        Games.c.game_id: game.game_id,
        Games.c.white_id: game.white_id,
        Games.c.black_id: game.black_id,
        Games.c.white_score: game.result.white_score,
        Games.c.black_score: game.result.black_score,
    })
    with conn.begin():
        conn.execute(insert_game)
        conn.execute(_make_query_to_update_rating(match.white))
        conn.execute(_make_query_to_update_rating(match.black))


def _find_many_by_ids(conn, table, ids):
    id_column = _get_id_column(table)
    query = table.select().where(id_column.in_(ids))
    rows = list(conn.execute(query))
    if len(rows) != len(ids):
        found_ids = [a_row[id_column] for a_row in rows]
        not_found_ids = set(ids) - set(found_ids)
        raise NotFound(f'ids {not_found_ids} do not exist in {table.name}')
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
    result = Functions.select().where(
        sa.and_(gte_than_random, is_active)).order_by(Functions.c.random).limit(1)
    return result


def _make_game_from_db_row(row: dict) -> models.Game:
    game_result = models.GameResult(
        white_score=row[Games.c.white_score],
        black_score=row[Games.c.black_score])
    return models.Game(
        game_id=row[Games.c.game_id],
        white_id=row[Games.c.white_id],
        black_id=row[Games.c.black_id],
        result=game_result)
