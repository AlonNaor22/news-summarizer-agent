import asyncio
import functools
import logging
import time


def timeit(func):
    """Decorator that logs the wall-clock duration of each call via the module's logger.

    Supports both sync and async functions — async coroutines are awaited so the
    measured time covers the whole call, not just coroutine creation.
    """
    logger = logging.getLogger(func.__module__)

    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = time.monotonic() - start
                logger.info("%s: %.2fs", func.__name__, elapsed)

        return async_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            logger.info("%s: %.2fs", func.__name__, elapsed)

    return wrapper
