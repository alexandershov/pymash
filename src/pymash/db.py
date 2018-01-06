import random
import typing as tp

import sqlalchemy as sa

from pymash import models
from pymash.tables import *


class BaseError(Exception):
    pass


class NotFound(BaseError):
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


def find_many_repos_by_ids(engine, repo_ids) -> tp.List[models.Repo]:
    rows = _find_many_by_ids(
        engine=engine,
        ids=repo_ids,
        table=Repos,
        id_column=Repos.c.repo_id)
    return list(map(_make_repo_from_db_row, rows))


def save_game_and_match(engine, game: models.Game, match: models.Match) -> None:
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(Games.insert().values(
                game_id=game.game_id,
                white_id=game.white_id,
                black_id=game.black_id,
                white_score=game.result.white_score,
                black_score=game.result.black_score,
            ))
            white_repo = match.white
            black_repo = match.black
            # TODO: is there a way to Repos.c.rating instead of rating=?
            # TODO: dry it up
            conn.execute(Repos.update().where(Repos.c.repo_id == white_repo.repo_id).values(rating=white_repo.rating))
            conn.execute(Repos.update().where(Repos.c.repo_id == black_repo.repo_id).values(rating=black_repo.rating))


def _find_many_by_ids(engine, ids, table, id_column):
    with engine.connect() as conn:
        rows = list(conn.execute(table.select().where(id_column.in_(ids))))
    if len(rows) != len(ids):
        # TODO: better error message
        raise NotFound
    return rows


def _make_find_random_function_query():
    x = random.random()
    # TODO: is there a better way?
    select_max_random = sa.select(
        columns=[sa.func.max(Functions.c.random)],
        from_obj=Functions).as_scalar()
    gt_than_random = Functions.c.random >= sa.func.least(x, select_max_random)
    result = Functions.select().where(gt_than_random).order_by(Functions.c.random).limit(1)
    return result


def _make_function_from_db_row(row: dict) -> models.Function:
    return models.Function(
        function_id=row[Functions.c.function_id],
        repo_id=row[Functions.c.repo_id],
        text=row[Functions.c.text])
