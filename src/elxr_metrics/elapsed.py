################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""module to calculate elapsed time"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from functools import wraps
from timeit import default_timer
from typing import Any, Callable, Generator

logger = logging.getLogger(__name__)


@contextmanager
def elapsed_timer() -> Generator[Callable[[], float], Any, None]:
    """context manager to measure the elaspsed time."""
    start = default_timer()

    def elapsed() -> float:
        """the elapsed time in seconds"""
        return default_timer() - start

    yield elapsed


def timing(f):
    """annotation to calculate elaspsed time of function."""

    @wraps(f)
    def wrap(*args, **kw):
        with elapsed_timer() as et:
            result = f(*args, **kw)
            logger.info("func:%r args:[%r, %r] took: %2.4f sec", f.__name__, args, kw, et())
            return result

    return wrap
