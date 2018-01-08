import json

import datetime as dt
from aiohttp import web

from pymash import db
from pymash import loggers
from pymash import models


class BaseError(Exception):
    pass


class NotFound(BaseError):
    pass


# TODO: add cron runner


async def post_game_finished_event(app: web.Application, game: models.Game) -> None:
    event = make_event_from_game(game)
    await _ensure_games_queue_is_ready(app)
    await app['games_queue'].send_message(MessageBody=json.dumps(event))


def make_event_from_game(game: models.Game) -> dict:
    return {
        'game_id': game.game_id,
        'white_id': game.white_id,
        'black_id': game.black_id,
        'white_score': game.result.white_score,
        'black_score': game.result.black_score,
        'occurred_at': dt.datetime.utcnow().isoformat(),
    }


async def _ensure_games_queue_is_ready(app):
    if 'games_queue' in app:
        return
    app['games_queue'] = await app['sqs_resource'].get_queue_by_name(QueueName=app['config'].sqs_games_queue_name)


def process_game_finished_event(engine, game: models.Game) -> None:
    try:
        white_fn, black_fn = db.find_many_functions_by_ids(engine, [game.white_id, game.black_id])
        white_repo, black_repo = db.find_many_repos_by_ids(engine, [white_fn.repo_id, black_fn.repo_id])
    except db.NotFound as exc:
        raise NotFound(str(exc)) from exc
    match = models.Match(white_repo, black_repo, game.result)
    match.change_ratings()
    try:
        db.save_game_and_match(engine, game, match)
    except db.GameResultChanged:
        loggers.queue.info('someone is trying to change results of finished game %s', game.game_id, exc_info=True)
