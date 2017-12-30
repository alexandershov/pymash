from pymash import models


async def find_matchup(connection) -> models.Matchup:
    async with connection.cursor() as cursor:
        pass
