import functools
import time


class log_time:
    def __init__(self, logger):
        self._logger = logger

    def log_time(self, fn):
        async def wrapper(*args, **kwargs):
            started_at = time.time()
            result = await fn(*args, **kwargs)
            finished_at = time.time()
            self._logger.info('%s.%s took %.3f', fn.__module__, fn.__qualname__, finished_at - started_at)
            return result

        functools.update_wrapper(wrapper, fn)
        return wrapper
