import functools
import logging
import time


def timeit(func):
    """Decorator that logs the wall-clock duration of each call via the module's logger."""
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            logger.info("%s: %.2fs", func.__name__, elapsed)

    return wrapper
