################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""test fixtures"""

from __future__ import annotations

import duckdb
import pytest


@pytest.fixture
def conn(monkeypatch):
    con = duckdb.connect(database=":memory:")  # in-memory DB for testing
    yield con
    con.close()


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """Remove requests.sessions.Session.request for all tests."""
    monkeypatch.delattr("requests.sessions.Session.request")
