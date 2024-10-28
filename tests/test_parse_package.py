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
from elxr_metrics.elxr_package import _parse_deb_name, _update_package_download, parse_mirror_elxr_dev_logs


@pytest.fixture(scope="function")
def log_entry():
    """create an log entry"""
    d = CloudFrontLogEntry()
    yield d


@pytest.mark.parametrize(
    "path, name",
    [
        ("/elxr/pool/main/e/edk2/uefi-ext4_202402-1elxr2_all.deb", "uefi-ext4"),
        ("/elxr/pool/main/z/zlib/zlib1g-dev_1.2.13.dfsg-1elxr1_arm64.deb", "zlib1g-dev"),
        ("/elxr/pool/main/a/apt/apt-utils_2.3.9_arm64.deb", "apt-utils"),
        ("/elxr/pool/main/c/curl/curl_7.68.0-1ubuntu2_arm64.deb", "curl"),
        ("/main/g/glib2.0/libglib2.0-0_2.74.6-2%252bdeb12u3_amd64.deb", "libglib2.0-0"),
        ("linux-image-imx-arm64_6.1.99-elxr2-2_arm64.deb", "linux-image-imx-arm64"),
        ("linux-image-6.1.0-23-imx-arm64_6.1.99-elxr2-2_arm64.deb", "linux-image-6.1.0-23-imx-arm64"),
        ("abc.deb", None),
        ("_.deb", None),
        ("/elxr/pool/main/g/gcc-12/libstdc%2b%2b6_12.2.0-14_amd64.deb", None),
    ],
)
def test_parse_deb_name(path, name):
    """test parsing deb name"""
    package_name = _parse_deb_name(path)

    assert package_name == name


@pytest.mark.parametrize(
    "init_content",
    [
        (None),
        (""),
        ("header"),
        ("Name,Download"),
    ],
)
def test_parse_package(tmp_path, init_content):
    """test parsing log"""
    path = Path(__file__).parent / "logs" / "mirror_elxr_dev"
    csv_file = tmp_path / "package_stats.csv"
    if init_content is not None:
        csv_file.write_text(init_content)
    parse_mirror_elxr_dev_logs(path, csv_file)
    expected = [("libglib2.0-0", 3), ("linux-image-imx-arm64", 2), ("linux-image-6.1.0-23-imx-arm64", 1)]
    actual = duckdb.read_csv(csv_file).fetchall()
    assert actual == expected

    parse_mirror_elxr_dev_logs(path, csv_file)
    expected = [("libglib2.0-0", 6), ("linux-image-imx-arm64", 4), ("linux-image-6.1.0-23-imx-arm64", 2)]
    actual = duckdb.read_csv(csv_file).fetchall()
    assert actual == expected


def test_update_package_download_false(mocker: MockerFixture, log_entry: CloudFrontLogEntry):
    """test checking logs that do not map to deb file"""
    conn = mocker.MagicMock(duckdb.DuckDBPyConnection)
    params = [
        (None, None),
        ("sc_content_type", "text/html"),
        ("sc_content_type", "application/vnd.debian.binary-package"),
        ("sc_status", 404),
        ("sc_status", 200),
        ("cs_uri_stem", "/elxr/dists/aria/main/binary-amd64/Packages.bz2"),
        ("cs_uri_stem", "/elxr/pool/main/l/less/less_590-2.1~deb12u2.dsc"),
        ("cs_uri_stem", "/elxr/pool/main/l/less/"),
        ("cs_uri_stem", "/elxr/pool/main/l/less/.deb"),
        ("cs_uri_stem", "/elxr/pool/main/l/less/abc.deb"),
    ]
    for name, value in params:
        if name:
            # log_entry.__setattr__(name, value)
            object.__setattr__(log_entry, name, value)
        _update_package_download(conn, log_entry)
        conn.execute.assert_not_called()


def test_update_package_download_true(mocker: MockerFixture, log_entry: CloudFrontLogEntry):
    """test checking logs that map to deb file"""
    conn = mocker.MagicMock(duckdb.DuckDBPyConnection)
    params = [
        ("sc_content_type", "application/vnd.debian.binary-package"),
        ("sc_status", 200),
        ("cs_uri_stem", "/elxr/pool/main/l/less/less_590-2.1~deb12u2_arm64.deb"),
    ]
    for name, value in params:
        object.__setattr__(log_entry, name, value)
    _update_package_download(conn, log_entry)
    conn.execute.assert_called_once()
