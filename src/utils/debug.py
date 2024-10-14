import time
from contextlib import contextmanager
from loguru import logger

@contextmanager
def log_runtime(name: str):
    """
    Context manager to log the runtime of a block of code.
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        elapsed_time = end_time - start_time

        # Depth 2 to escape this function and contextlib
        logger_ = logger.opt(depth=2)
        logger_.info(f"{name} took {elapsed_time:.1f} seconds")

