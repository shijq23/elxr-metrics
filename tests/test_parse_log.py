################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
from __future__ import annotations

from pathlib import Path

import pytest

from elxr_metrics.cloudfront_log import CloudFrontLogEntry, _to_object, parse_cloudfront_log


@pytest.mark.parametrize(
    "value, field, result",
    [
        (
            "/elxr/pool/main/g/gcc-12/libstdc%2b%2b6_12.2.0-14_amd64.deb",
            CloudFrontLogEntry.__dataclass_fields__["cs_uri_stem"],
            "/elxr/pool/main/g/gcc-12/libstdc++6_12.2.0-14_amd64.deb",
        ),
        (
            "/elxr/pool/main/g/gcc-12/libstdc%252b%252b6_12.2.0-14_amd64.deb",
            CloudFrontLogEntry.__dataclass_fields__["cs_uri_stem"],
            "/elxr/pool/main/g/gcc-12/libstdc++6_12.2.0-14_amd64.deb",
        ),
    ],
)
def test_to_object(value, field, result):
    actual = _to_object(value, field)
    assert actual == result


@pytest.mark.parametrize(
    "path",
    [("A65ZZCR5KMGAR8.2024-10-01-18.2d243ee0.gz")],
)
def test_parse_log(path):
    """test parsing log"""
    path = Path(__file__).parent / "logs" / "elxr_org" / path
    entries = list(parse_cloudfront_log(path))

    assert len(entries) == 5
    assert entries[0].cs_uri_stem == "/"
    assert entries[1].c_ip == "11.22.33.44"
    assert entries[2].cs_method == "GET"
    assert entries[3].sc_status == 200
    assert entries[4].cs_protocol == "https"
