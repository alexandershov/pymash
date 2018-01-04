from pymash import models


async def post_game_finished_event(game: models.Game) -> None:
    raise NotImplementedError
