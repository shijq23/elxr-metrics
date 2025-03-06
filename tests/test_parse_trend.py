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
import maxminddb
import pytest

from elxr_metrics.elxr_org_trend import _country_lookup, parse_elxr_org_logs


@pytest.mark.parametrize(
    "init_content",
    [
        (None),
        (""),
        ("header"),
        ("TimeBucket,ViewCount,UniqueUser"),
    ],
)
def test_parse_trend_init_content(tmp_path, init_content):
    """test parsing log with different initial content"""
    path = Path(__file__).parent / "logs" / "elxr_org"
    csv_file = tmp_path / "elxr_org_view.csv"
    if init_content is not None:
        csv_file.write_text(init_content)

    # First parse
    parse_elxr_org_logs(path, csv_file)
    df = duckdb.read_csv(csv_file)
    actual = df.fetchall()
    actual_set = set(actual)

    # Verify first parse results
    assert len(actual) > 0
    assert (datetime.datetime(2074, 9, 22, 18, 0), 3, 2) in actual_set
    assert (datetime.datetime(2074, 9, 25, 18, 0), 3, 2) in actual_set

    # Second parse - should double the counts
    parse_elxr_org_logs(path, csv_file)
    df = duckdb.read_csv(csv_file)
    actual = df.fetchall()
    actual_set = set(actual)

    # Verify counts doubled after second parse
    assert (datetime.datetime(2074, 9, 22, 18, 0), 6, 4) in actual_set
    assert (datetime.datetime(2074, 9, 25, 18, 0), 6, 4) in actual_set


def test_parse_trend_log(tmp_path):
    """test parsing log"""
    path = Path(__file__).parent / "logs" / "elxr_org"
    csv_file = tmp_path / "elxr_org_view.csv"

    # First parse
    parse_elxr_org_logs(path, csv_file)
    df = duckdb.read_csv(csv_file)
    actual = df.fetchall()

    # Verify first parse results
    assert len(actual) > 0
    # Convert actual results to a set of tuples for comparison
    actual_set = set(actual)
    # Verify specific expected entries exist
    assert (datetime.datetime(2074, 9, 22, 18, 0), 3, 2) in actual_set
    assert (datetime.datetime(2074, 9, 25, 18, 0), 3, 2) in actual_set

    # Second parse - should double the counts
    parse_elxr_org_logs(path, csv_file)
    df = duckdb.read_csv(csv_file)
    actual = df.fetchall()
    actual_set = set(actual)

    # Verify counts doubled after second parse
    assert (datetime.datetime(2074, 9, 22, 18, 0), 6, 4) in actual_set
    assert (datetime.datetime(2074, 9, 25, 18, 0), 6, 4) in actual_set


@pytest.mark.parametrize(
    "ip, code",
    [
        (None, "N/A"),
        ("", "N/A"),
        (" ", "N/A"),
        ("-", "N/A"),
        ("8.8.8.8", "US"),
        ("67.69.172.12", "CA"),
        ("210.227.116.101", "JP"),
        ("203.127.232.194", "SG"),
        ("114.114.114.114", "CN"),
        ("212.27.40.240", "FR"),
        ("168.126.63.1", "KR"),
        ("170.81.34.76", "CR"),
        ("27.7.22.190", "IN"),
        ("88.247.12.187", "TR"),  # Turkey
        ("91.220.37.68", "NL"),  # Netherlands
        ("999.999.999.999", "N/A"),
        ("77.111.247.13", "NO"),
        # ("68.0.30.21", "US"),  # US
    ],
)
def test_country_lookup(ip, code):
    """test country lookup"""
    codes = _country_lookup(ip)[0]
    assert codes == code
    if codes == "N/A":
        return
    # verify countries.csv has the country name and coordinates
    csv_path: Path = Path(__file__).parent.parent / "public" / "countries.csv"
    countries = [row[0] for row in duckdb.read_csv(csv_path).fetchall()]
    assert codes in countries


@pytest.mark.skip(reason="This test is slow")
def test_all_country_codes():
    """test all country codes are in countries.csv.

    This test ensures all country codes in GeoLite2-Country.mmdb are in countries.csv.
    """
    country_codes = _get_country_codes()
    csv_path: Path = Path(__file__).parent.parent / "public" / "countries.csv"
    countries = [row[0] for row in duckdb.read_csv(csv_path).fetchall()]
    assert country_codes <= set(countries)


def _get_country_codes():
    """dump country codes from mmdb file.

    Execution of this function is not required for test_country_lookup.
    It is used to verify the country codes are all in countries.csv.
    Running time is about 200 seconds.
    """
    DB_PATH = r"GeoLite2-Country/GeoLite2-Country.mmdb"
    country_codes: set[str] = set()
    with maxminddb.Reader(DB_PATH) as reader:
        # All countries are stored in metadata's country ISO code mappings
        for record in reader:
            r = record[1]
            c = r.get("country") or r.get("registered_country")
            # name = r.get("registered_country", {}).get("names", {}).get("en")
            # country_codes.add(str(name))
            code = c.get("iso_code")
            country_codes.add(str(code))
    return country_codes
