import asyncio
import functools
import time


# noinspection PyUnusedLocal
def _get_args_str(*args, **kwargs):
    return ''


class log_time:
    def __init__(self, logger, get_args_str_or_str=_get_args_str):
        self._logger = logger
        self._get_args_str_or_str = get_args_str_or_str
        self._started_at = None
        self._finished_at = None
        self._fn = None

    def __call__(self, fn):
        if asyncio.iscoroutinefunction(fn):
            async def wrapper(*args, **kwargs):
                self._before_fn(fn)
                result = await fn(*args, **kwargs)
                self._after_fn(*args, **kwargs)
                return result
        else:
            def wrapper(*args, **kwargs):
                self._before_fn(fn)
                result = fn(*args, **kwargs)
                self._after_fn(*args, **kwargs)
                return result

        return functools.update_wrapper(wrapper, fn)

    def __enter__(self):
        self._started_at = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._started_at is not None
        assert isinstance(self._get_args_str_or_str, str)
        duration = time.time() - self._started_at
        self._logger.info('%s took %.3fs', self._get_args_str_or_str, duration)

    def _before_fn(self, fn):
        self._fn = fn
        self._started_at = time.time()

    def _after_fn(self, *args, **kwargs):
        self._finished_at = time.time()
        args_str = self._get_args_str_or_str(*args, **kwargs)
        self._logger.info(
            '%s.%s(%s) took %.3fs', self._fn.__module__, self._fn.__qualname__, args_str,
            self._finished_at - self._started_at)
