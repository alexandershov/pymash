import typing as tp

from pymash import models
from pymash import tables


async def find_repos_order_by_rating(engine) -> tp.List[models.Repo]:
    repos = []
    async with engine.acquire() as conn:
        query = tables.sa_repos.select().order_by(tables.sa_repos.c.rating.desc())
        async for a_row in conn.execute(query):
            repos.append(a_row)
    return repos


async def find_matchup(connection) -> models.Matchup:
    async with connection.cursor() as cursor:
        pass


def _make_repo_from_db_row(row: dict) -> models.Repo:
    return models.Repo(
        repo_id=row[tables.sa_repos.c.id],
        name=row[tables.sa_repos.c.name],
        url=row[tables.sa_repos.c.url],
        rating=row[tables.sa_repos.c.rating])
