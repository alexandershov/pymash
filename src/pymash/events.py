import json

import datetime as dt
from aiohttp import web

from pymash import db
from pymash import loggers
from pymash import models
from pymash import utils


class BaseError(Exception):
    pass


class DeletedFromDb(BaseError):
    pass


@utils.log_time(loggers.web)
async def post_game_finished_event(app: web.Application, game: models.Game) -> None:
    event = make_game_finished_event_from_game(game)
    await _ensure_games_queue_is_ready(app)
    await app['games_queue'].send_message(MessageBody=json.dumps(event))


def make_game_finished_event_from_game(game: models.Game) -> dict:
    return {
        'game_id': game.game_id,
        'white_id': game.white_id,
        'black_id': game.black_id,
        'white_score': game.result.white_score,
        'black_score': game.result.black_score,
        'occurred_at': dt.datetime.utcnow().isoformat(),
    }


def parse_game_finished_event(data: dict) -> models.Game:
    result = models.GameResult(data['white_score'], data['black_score'])
    return models.Game(
        game_id=data['game_id'],
        white_id=data['white_id'],
        black_id=data['black_id'],
        result=result)


@utils.log_time(loggers.web)
async def _ensure_games_queue_is_ready(app):
    if 'games_queue' in app:
        return
    app['games_queue'] = await app['sqs_resource'].get_queue_by_name(QueueName=app['config'].sqs_games_queue_name)


@utils.log_time(loggers.games_queue)
def process_game_finished_event(engine, game: models.Game) -> None:
    loggers.games_queue.info(
        'processing game between %s and %s, result (%s - %s)',
        game.white_id, game.black_id, game.result.white_score, game.result.black_score)
    try:
        white_fn, black_fn = db.find_many_functions_by_ids(engine, [game.white_id, game.black_id])
        white_repo, black_repo = db.find_many_repos_by_ids(engine, [white_fn.repo_id, black_fn.repo_id])
    except db.NotFound as exc:
        raise DeletedFromDb(str(exc)) from exc
    match = models.Match(white_repo, black_repo, game.result)
    loggers.games_queue.info(
        'before: %s has rating %s, %s has rating %s',
        white_repo.name, white_repo.rating,
        black_repo.name, black_repo.rating)
    match.change_ratings()
    loggers.games_queue.info(
        'after: %s has rating %s, %s has rating %s',
        white_repo.name, white_repo.rating,
        black_repo.name, black_repo.rating)
    try:
        db.save_game_and_match(engine, game, match)
    except db.GameResultChanged:
        loggers.games_queue.info('someone is trying to change results of finished game %s', game.game_id, exc_info=True)
