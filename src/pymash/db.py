import random
import typing as tp

import sqlalchemy as sa
import sqlalchemy.exc as sa_exc
from sqlalchemy.dialects.postgresql import insert

from pymash import models
from pymash.tables import *


class BaseError(Exception):
    pass


class NotFound(BaseError):
    pass


class GameResultChanged(BaseError):
    pass


async def find_repos_order_by_rating(engine) -> tp.List[models.Repo]:
    repos = []
    async with engine.acquire() as conn:
        query = Repos.select().order_by(Repos.c.rating.desc())
        async for a_row in conn.execute(query):
            repos.append(a_row)
    return repos


def _make_repo_from_db_row(row: dict) -> models.Repo:
    return models.Repo(
        repo_id=row[Repos.c.repo_id],
        name=row[Repos.c.name],
        url=row[Repos.c.url],
        rating=row[Repos.c.rating])


async def try_to_find_two_random_functions(engine) -> tp.List[models.Function]:
    select_some_function = _make_find_random_function_query()
    select_another_function = _make_find_random_function_query()
    select_two_functions = select_some_function.union_all(select_another_function)
    async with engine.acquire() as conn:
        rows = await conn.execute(select_two_functions)
    return list(map(_make_function_from_db_row, rows))


def find_many_functions_by_ids(engine, function_ids) -> tp.List[models.Function]:
    rows = _find_many_by_ids(
        engine=engine,
        ids=function_ids,
        table=Functions,
        id_column=Functions.c.function_id)
    return list(map(_make_function_from_db_row, rows))


def find_game_by_id(engine, game_id) -> models.Game:
    rows = _find_many_by_ids(
        engine=engine,
        ids=[game_id],
        table=Games,
        id_column=Games.c.game_id)
    assert len(rows) == 1
    return _make_game_from_db_row(rows[0])


def find_many_repos_by_ids(engine, repo_ids) -> tp.List[models.Repo]:
    rows = _find_many_by_ids(
        engine=engine,
        ids=repo_ids,
        table=Repos,
        id_column=Repos.c.repo_id)
    return list(map(_make_repo_from_db_row, rows))


def save_game_and_match(engine, game: models.Game, match: models.Match) -> None:
    # TODO: check that doing execution_options doesn't permanently change connection when it will be returned to pool
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        try:
            with conn.begin():
                conn.execute(Games.insert().values({
                    Games.c.game_id: game.game_id,
                    Games.c.white_id: game.white_id,
                    Games.c.black_id: game.black_id,
                    Games.c.white_score: game.result.white_score,
                    Games.c.black_score: game.result.black_score,
                }))
                conn.execute(_make_update_rating_query(match.white))
                conn.execute(_make_update_rating_query(match.black))
        except sa_exc.IntegrityError as exc:
            assert Games.c.game_id.name in exc.params
            game_from_db = find_game_by_id(engine, game.game_id)
            if game_from_db.result != game.result:
                raise GameResultChanged


def save_github_repo(engine, github_repo: models.GithubRepo) -> None:
    with engine.connect() as conn:
        insert_data = {
            Repos.c.name: github_repo.name,
            Repos.c.url: github_repo.url,
            Repos.c.rating: models.Repo.DEFAULT_RATING,
        }
        update_data = {
            Repos.c.name: github_repo.name,
            Repos.c.url: github_repo.url,
        }
        conn.execute(insert(Repos).values(insert_data).on_conflict_do_update(update_data))


def _find_many_by_ids(engine, ids, table, id_column):
    # TODO: is there a way to determine id_column automatically from table
    with engine.connect() as conn:
        rows = list(conn.execute(table.select().where(id_column.in_(ids))))
    if len(rows) != len(ids):
        row_ids = [a_row[id_column] for a_row in rows]
        not_found_ids = set(ids) - set(row_ids)
        msg = f'ids {not_found_ids} does not exist in {table.name}'
        raise NotFound(msg)
    return rows


def _make_update_rating_query(repo: models.Repo):
    return Repos.update().where(Repos.c.repo_id == repo.repo_id).values(
        {Repos.c.rating: repo.rating})


def _make_find_random_function_query():
    x = random.random()
    select_max_random = Functions.select().with_only_columns(
        [sa.func.max(Functions.c.random)]).as_scalar()
    gt_than_random = Functions.c.random >= sa.func.least(x, select_max_random)
    result = Functions.select().where(gt_than_random).order_by(Functions.c.random).limit(1)
    return result


def _make_function_from_db_row(row: dict) -> models.Function:
    return models.Function(
        function_id=row[Functions.c.function_id],
        repo_id=row[Functions.c.repo_id],
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
