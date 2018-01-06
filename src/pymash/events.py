from pymash import db
from pymash import models


async def post_game_finished_event(game: models.Game) -> None:
    # TODO: implement it
    raise NotImplementedError


def process_game_finished_event(engine, game: models.Game) -> None:
    white_function, black_function = db.find_many_functions_by_ids(engine, [game.white_id, game.black_id])
    white_repo, black_repo = db.find_many_repos_by_ids(engine, [white_function.repo_id, black_function.repo_id])
    match = models.Match(white_repo, black_repo, game.result)
    match.change_ratings()
    db.insert_game(engine, game)
    db.save_match(engine, match)
