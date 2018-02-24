import datetime as dt
import json

from aiohttp import web

from pymash import db
from pymash import loggers
from pymash import models
from pymash import type_aliases as ta
from pymash import utils


class BaseError(Exception):
    pass


class DeletedFromDb(BaseError):
    pass


@utils.log_time(loggers.web)
async def post_game_finished_event(request: web.Request, game: models.Game) -> None:
    app = request.app
    event = make_game_finished_event(game, _get_user_ip(request))
    await _ensure_games_queue_is_ready(app)
    loggers.web.info('sending game_finished event %r', event)
    await app['games_queue'].send_message(MessageBody=json.dumps(event))


def make_game_finished_event(game: models.Game, ip: str) -> dict:
    return {
        'game_id': game.game_id,
        'white_id': game.white_id,
        'black_id': game.black_id,
        'white_score': game.result.white_score,
        'black_score': game.result.black_score,
        'occurred_at': dt.datetime.utcnow().isoformat(timespec='seconds'),
        'ip': ip,
    }


def parse_game_finished_event_as_game(data: dict) -> models.Game:
    result = models.GameResult(data['white_score'], data['black_score'])
    return models.Game(
        game_id=data['game_id'],
        white_id=data['white_id'],
        black_id=data['black_id'],
        result=result)


def parse_game_finished_event_as_game_attempt(data: dict) -> models.GameAttempt:
    return models.GameAttempt(
        ip=data['ip'],
        at=dt.datetime.strptime(data['occurred_at'], '%Y-%m-%dT%H:%M:%S'))


@utils.log_time(loggers.web)
async def _ensure_games_queue_is_ready(app):
    if 'games_queue' in app:
        return
    queue_name = app['config'].sqs_games_queue_name
    app['games_queue'] = await app['sqs_resource'].get_queue_by_name(QueueName=queue_name)


@utils.log_time(loggers.games_queue)
def process_game_finished_event(engine: ta.Engine, game: models.Game) -> None:
    loggers.games_queue.info('processing game %s', game)
    try:
        white_repo, black_repo = db.find_many_repos_by_function_ids(
            engine, game.white_id, game.black_id)
    except db.NotFound as exc:
        raise DeletedFromDb(str(exc)) from exc

    match = models.Match(white_repo, black_repo, game.result)
    loggers.games_queue.info('before: white is %s; black is %s', white_repo, black_repo)
    match.change_ratings()
    try:
        db.save_game_and_match(engine, game, match)
    except db.GameResultChanged:
        loggers.games_queue.info('someone is trying to change result of finished game %s', game, exc_info=True)
    except db.NotFound as exc:
        raise DeletedFromDb(str(exc)) from exc
    else:
        loggers.games_queue.info('after: white is %s; black is %s', white_repo, black_repo)


def _get_user_ip(request: web.Request) -> str:
    return request.headers['X-Forwarded-For'].split(', ')[0]
