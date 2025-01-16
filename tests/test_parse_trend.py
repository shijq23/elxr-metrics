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


@pytest.mark.parametrize(
    "ip, country",
    [
        (None, "N/A"),
        ("", "N/A"),
        (" ", "N/A"),
        ("-", "N/A"),
        ("8.8.8.8", "United States"),
        ("67.69.172.12", "Canada"),
        ("210.227.116.101", "Japan"),
        ("203.127.232.194", "Singapore"),
        ("114.114.114.114", "China"),
        ("212.27.40.240", "France"),
        ("168.126.63.1", "South Korea"),
        ("170.81.34.76", "Costa Rica"),
        ("27.7.22.190", "India"),
        ("88.247.12.187", "Türkiye"),  # Turkey
        ("91.220.37.68", "The Netherlands"),  # Netherlands
        ("999.999.999.999", "N/A"),
    ],
)
def test_country_lookup(ip, country):
    """test country lookup"""
    actual = _country_lookup(ip)
    assert actual == country
    if actual == "N/A":
        return
    # verify countries.csv has the country name and coordinates
    csv_path: Path = Path(__file__).parent.parent / "public" / "countries.csv"
    countries = [row[3] for row in duckdb.read_csv(csv_path).fetchall()]
    assert country in countries


@pytest.mark.skip(reason="This test is slow")
def test_all_country_names():
    """test all country names are in countries.csv"""
    country_names = _get_country_names()
    csv_path: Path = Path(__file__).parent.parent / "public" / "countries.csv"
    countries = [row[3] for row in duckdb.read_csv(csv_path).fetchall()]
    assert country_names <= set(countries)


def _get_country_names():
    """dump country names from mmdb file.

    Execution of this function is not required for test_country_lookup.
    It is used to verify the country names are all in countries.csv.
    Running time is about 200 seconds.
    """
    DB_PATH = r"GeoLite2-Country/GeoLite2-Country.mmdb"
    country_names: set[str] = set()
    with maxminddb.Reader(DB_PATH) as reader:
        # All countries are stored in metadata's country ISO code mappings
        for record in reader:
            r = record[1]
            name = r.get("registered_country", {}).get("names", {}).get("en")
            country_names.add(str(name))
    return country_names
