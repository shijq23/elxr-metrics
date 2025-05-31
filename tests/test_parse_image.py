################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest
from pytest_mock import MockerFixture

from elxr_metrics.cloudfront_log import CloudFrontLogEntry
from elxr_metrics.elxr_image import _parse_image_name, _update_image_download, parse_downloads_elxr_dev_logs


@pytest.fixture(scope="function")
def log_entry():
    """create an log entry"""
    d = CloudFrontLogEntry()
    yield d


@pytest.mark.parametrize(
    "path, name",
    [
        ("/elxr-12.6.1.0-amd64-CD-1.iso", "elxr-12.6.1.0-amd64-CD-1.iso"),
        ("/elxr-minimal-ostree-imx8-0.1-arm64.img.zst", "elxr-minimal-ostree-imx8-0.1-arm64.img.zst"),
        ("/elxr-tegra-12.6.1.0-arm64.tar.gz", "elxr-tegra-12.6.1.0-arm64.tar.gz"),
        ("/elxr-tegra-12.6.1.0-arm64.tar.gz.sha256.txt", None),
        ("/elxr-12.6.1.0-amd64-CD-1.iso.sha256", None),
        ("/elxr-/.iso", None),
        ("/elxr-/a.iso", None),
    ],
)
def test_parse_image_name(path, name):
    """test parsing image name"""
    image_name = _parse_image_name(path)

    assert image_name == name


@pytest.mark.parametrize(
    "init_content",
    [
        (None),
        (""),
        ("header"),
        ("Name,Download"),
    ],
)
def test_parse_image(tmp_path, init_content):
    """test parsing log"""
    path = Path(__file__).parent / "logs" / "downloads_elxr_dev"
    csv_file = tmp_path / "image_stats.csv"

    # Ensure a clean state for csv_file for each parameterized run
    if csv_file.exists():
        csv_file.unlink()

    if init_content is not None:
        if init_content: # only write if non-empty string
             csv_file.write_text(init_content)
        elif init_content == "": # if empty string, create empty file
             csv_file.touch()
    # If init_content is None, file does not exist, which is a valid test scenario.

    parse_downloads_elxr_dev_logs(path, csv_file)

    # Expected counts from a single pass over the logs.
    # Note: The log file contains "elxr-12.6.1.0-amd64-CD-1.iso" 3 times and "elxr-image-testdata.zst" 2 times.
    expected = [("elxr-12.6.1.0-amd64-CD-1.iso", 3), ("elxr-image-testdata.zst", 2)]

    actual_raw = duckdb.read_csv(csv_file).fetchall()
    actual = []
    if actual_raw:
        if len(actual_raw[0]) == 2 and isinstance(actual_raw[0][0], str) and isinstance(actual_raw[0][1], (int, float)):
             actual = [(str(row[0]), int(row[1])) for row in actual_raw]
        else: # Fallback for safety, though not expected for this test's data
            actual = [tuple(row) for row in actual_raw]

    # Use set comparison for order-insensitivity
    assert set(actual) == set(expected)


def test_update_package_download_false(mocker: MockerFixture, log_entry: CloudFrontLogEntry):
    """test checking logs that do not map to deb file"""
    conn = mocker.MagicMock(duckdb.DuckDBPyConnection)
    params = [
        (None, None),
        ("sc_content_type", "text/html"),
        ("sc_content_type", "application/x-iso9660-image"),
        ("sc_status", 404),
        ("sc_status", 200),
        ("x_edge_result_type", "Error"),
        ("x_edge_result_type", "Hit"),
        ("sc_bytes", 100),
        ("sc_bytes", 666000000),
        ("cs_uri_stem", "/abc.iso"),
        ("cs_uri_stem", "/elxr/dists/aria/main/binary-amd64/Packages.iso"),
        ("cs_uri_stem", "/elxr-/pool/main/l/less/"),
        ("cs_uri_stem", "/elxr-/pool/main/l/less/.iso"),
        ("cs_uri_stem", "/elxr-/pool/main/l/less/abc.iso"),
    ]
    for name, value in params:
        if name:
            # log_entry.__setattr__(name, value)
            object.__setattr__(log_entry, name, value)
        _update_image_download(conn, log_entry)
        conn.execute.assert_not_called()


def test_update_image_download_true(mocker: MockerFixture, log_entry: CloudFrontLogEntry):
    """test checking logs that map to iso file"""
    conn = mocker.MagicMock(duckdb.DuckDBPyConnection)
    params = [
        ("sc_content_type", "application/x-iso9660-image"),
        ("sc_status", 200),
        ("x_edge_result_type", "Miss"),
        ("sc_bytes", 777000000),
        ("cs_uri_stem", "elxr-12.6.1.0-amd64-CD-1.iso"),
    ]
    for name, value in params:
        object.__setattr__(log_entry, name, value)
    _update_image_download(conn, log_entry)
    conn.execute.assert_called_once()
