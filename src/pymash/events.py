import decimal


async def post_game_finished_event(game_id: int, white_id: int, black_id: int,
                                   white_score: int,
                                   black_score: int) -> None:
    raise NotImplementedError
