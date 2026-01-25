"""Logging utilities that work both in and out of Prefect context."""
import logging
from prefect import get_run_logger
from prefect.exceptions import MissingContextError
from loguru import logger as loguru_logger


def get_logger():
    """
    Get a logger that works both in Prefect context and outside (e.g., tests).

    Returns:
        - Prefect logger if running in a flow/task context
        - Loguru logger otherwise (for tests, standalone scripts)
    """
    try:
        return get_run_logger()
    except MissingContextError:
        # No Prefect context - use loguru (e.g., in tests)
        return loguru_logger
