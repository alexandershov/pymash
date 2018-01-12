import functools
import time

import asyncio


# noinspection PyUnusedLocal
def _get_args_str(*args, **kwargs):
    return ''


class log_time:
    def __init__(self, logger, get_args_str_or_str=_get_args_str):
        self._logger = logger
        self._get_args_str_or_str = get_args_str_or_str
        self._started_at = None

    def __call__(self, fn):
        if asyncio.iscoroutinefunction(fn):
            async def wrapper(*args, **kwargs):
                started_at = time.time()
                result = await fn(*args, **kwargs)
                finished_at = time.time()
                self._logger.info(
                    '%s.%s(%s) took %.3fs', fn.__module__, fn.__qualname__, self._get_args_str_or_str(*args, **kwargs),
                    finished_at - started_at)
                return result
        else:
            def wrapper(*args, **kwargs):
                started_at = time.time()
                result = fn(*args, **kwargs)
                finished_at = time.time()
                self._logger.info(
                    '%s.%s(%s) took %.3fs', fn.__module__, fn.__qualname__, self._get_args_str_or_str(*args, **kwargs),
                    finished_at - started_at)
                return result

        return functools.update_wrapper(wrapper, fn)

    def __enter__(self):
        self._started_at = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._started_at is not None
        finished_at = time.time()
        self._logger.info('%s took %.3fs', self._get_args_str_or_str, finished_at - self._started_at)
