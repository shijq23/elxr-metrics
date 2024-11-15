################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
from __future__ import annotations

import datetime
from pathlib import Path

import duckdb
import pytest

from elxr_metrics.elxr_org_trend import parse_elxr_org_logs


@pytest.mark.parametrize(
    "init_content",
    [
        (None),
        (""),
        ("header"),
        ("TimeBucket,ViewCount,UniqueUser"),
    ],
)
def test_parse_trend(tmp_path, init_content):
    """test parsing log"""
    path = Path(__file__).parent / "logs" / "elxr_org"
    csv_file = tmp_path / "elxr_org_view.csv"
    if init_content is not None:
        csv_file.write_text(init_content)
    parse_elxr_org_logs(path, csv_file)
    expected = [
        (datetime.datetime(2074, 9, 22, 18, 0), 3, 2),
        (datetime.datetime(2074, 9, 25, 18, 0), 3, 2),
    ]
    actual = duckdb.read_csv(csv_file).fetchall()
    assert set(expected) <= set(actual)

    parse_elxr_org_logs(path, csv_file)
    expected = [
        (datetime.datetime(2074, 9, 22, 18, 0), 6, 4),
        (datetime.datetime(2074, 9, 25, 18, 0), 6, 4),
    ]
    actual = duckdb.read_csv(csv_file).fetchall()
    assert set(expected) <= set(actual)
