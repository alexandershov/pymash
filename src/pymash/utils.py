import asyncio
import functools
import time
import typing as tp


# noinspection PyUnusedLocal
def _get_args_str(*args, **kwargs):
    return ''


class log_time:
    def __init__(self, logger, get_args_str_or_str: tp.Union[tp.Callable, str] = _get_args_str):
        self._logger = logger
        self._get_args_str_or_str = get_args_str_or_str
        self._started_at = None
        self._finished_at = None
        self._fn = None

    def __call__(self, fn):
        if asyncio.iscoroutinefunction(fn):
            async def wrapper(*args, **kwargs):
                with log_time(self._logger, self._get_fn_call_str(fn, *args, **kwargs)):
                    return await fn(*args, **kwargs)
        else:
            def wrapper(*args, **kwargs):
                with log_time(self._logger, self._get_fn_call_str(fn, *args, **kwargs)):
                    return fn(*args, **kwargs)

        return functools.update_wrapper(wrapper, fn)

    def __enter__(self):
        self._started_at = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert self._started_at is not None
        assert isinstance(self._get_args_str_or_str, str)
        duration = time.time() - self._started_at
        self._logger.info('%s took %.3fs', self._get_args_str_or_str, duration)

    def _get_fn_call_str(self, fn, *args, **kwargs) -> str:
        args_str = self._get_args_str_or_str(*args, **kwargs)
        return f'{fn.__module__}.{fn.__qualname__}({args_str})'
