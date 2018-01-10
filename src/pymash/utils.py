import functools
import time

import asyncio


def log_time(logger):
    def decorator(fn):
        if asyncio.iscoroutinefunction(fn):
            async def wrapper(*args, **kwargs):
                started_at = time.time()
                result = await fn(*args, **kwargs)
                finished_at = time.time()
                logger.info('%s.%s took %.3fs', fn.__module__, fn.__qualname__, finished_at - started_at)
                return result
        else:
            def wrapper(*args, **kwargs):
                started_at = time.time()
                result = fn(*args, **kwargs)
                finished_at = time.time()
                logger.info('%s.%s took %.3fs', fn.__module__, fn.__qualname__, finished_at - started_at)
                return result

        return functools.update_wrapper(wrapper, fn)

    return decorator
