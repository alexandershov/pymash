from pymash import db
from pymash import models


class BaseError(Exception):
    pass


class NotFound(BaseError):
    pass


# TODO: add cron runner and connect post/process functions to sqs


async def post_game_finished_event(game: models.Game) -> None:
    # TODO: implement it
    raise NotImplementedError


def process_game_finished_event(engine, game: models.Game) -> None:
    try:
        white_fn, black_fn = db.find_many_functions_by_ids(engine, [game.white_id, game.black_id])
        white_repo, black_repo = db.find_many_repos_by_ids(engine, [white_fn.repo_id, black_fn.repo_id])
    except db.NotFound:
        raise NotFound
    match = models.Match(white_repo, black_repo, game.result)
    match.change_ratings()
    try:
        db.save_game_and_match(engine, game, match)
    except db.GameResultChanged:
        print(f'someone is trying to change results of finished game {game.game_id}')
