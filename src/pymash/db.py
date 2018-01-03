import typing as tp

from pymash import models
from pymash import tables


async def find_repos_order_by_rating(engine) -> tp.List[models.Repo]:
    repos = []
    async with engine.acquire() as conn:
        query = tables.Repos.select().order_by(tables.Repos.c.rating.desc())
        async for a_row in conn.execute(query):
            repos.append(a_row)
    return repos


async def find_matchup(connection) -> models.Matchup:
    async with connection.cursor() as cursor:
        pass


def _make_repo_from_db_row(row: dict) -> models.Repo:
    return models.Repo(
        repo_id=row[tables.Repos.c.id],
        name=row[tables.Repos.c.name],
        url=row[tables.Repos.c.url],
        rating=row[tables.Repos.c.rating])
