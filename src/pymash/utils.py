import functools
import time

import asyncio


def _get_args_str(*args, **kwargs):
    return ''


def log_time(logger, get_args_str=_get_args_str):
    def decorator(fn):
        if asyncio.iscoroutinefunction(fn):
            async def wrapper(*args, **kwargs):
                started_at = time.time()
                result = await fn(*args, **kwargs)
                finished_at = time.time()
                logger.info(
                    '%s.%s(%s) took %.3fs', fn.__module__, fn.__qualname__, get_args_str(*args, **kwargs),
                    finished_at - started_at)
                return result
        else:
            def wrapper(*args, **kwargs):
                started_at = time.time()
                result = fn(*args, **kwargs)
                finished_at = time.time()
                logger.info(
                    '%s.%s(%s) took %.3fs', fn.__module__, fn.__qualname__, get_args_str(*args, **kwargs),
                    finished_at - started_at)
                return result

        return functools.update_wrapper(wrapper, fn)

    return decorator
