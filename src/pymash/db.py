import random
import typing as tp

from pymash import models
from pymash.tables import *


async def find_repos_order_by_rating(engine) -> tp.List[models.Repo]:
    repos = []
    async with engine.acquire() as conn:
        query = Repos.select().order_by(Repos.c.rating.desc())
        async for a_row in conn.execute(query):
            repos.append(a_row)
    return repos


async def find_matchup():
    return None


def _make_repo_from_db_row(row: dict) -> models.Repo:
    return models.Repo(
        repo_id=row[Repos.c.id],
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


def _make_find_random_function_query():
    x = random.random()
    return (Functions
        .select()
        .where(Functions.c.random > x)
        .order_by(Functions.c.random)
        .limit(1))


def _make_function_from_db_row(row: dict) -> models.Function:
    return models.Function(
        function_id=row[Functions.c.id],
        repo_id=row[Functions.c.repo_id],
        text=row[Functions.c.text])
