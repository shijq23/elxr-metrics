################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""module to parse cloudfront log files"""

from __future__ import annotations

import datetime
import gzip
import urllib.parse
from dataclasses import Field, dataclass, fields
from http import cookies
from pathlib import Path
from typing import Any, Generator


@dataclass(frozen=True)
class CloudFrontLogEntry:  # pylint: disable=too-many-instance-attributes
    """cloudfront log entry"""

    date: datetime.date | None = None
    time: datetime.time | None = None
    x_edge_location: str | None = None
    sc_bytes: int | None = None
    c_ip: str | None = None
    cs_method: str | None = None
    cs_host: str | None = None
    cs_uri_stem: str | None = None
    sc_status: int | None = None
    cs_referrer: str | None = None
    cs_user_agent: str | None = None
    cs_uri_query: dict | None = None
    cs_cookie: cookies.SimpleCookie | None = None
    x_edge_result_type: str | None = None
    x_edge_request_id: str | None = None
    x_host_header: str | None = None
    cs_protocol: str | None = None
    cs_bytes: int | None = None
    time_taken: float | None = None
    x_forwarded_for: str | None = None
    ssl_protocol: str | None = None
    ssl_cipher: str | None = None
    x_edge_response_result_type: str | None = None
    cs_protocol_version: str | None = None
    fle_status: str | None = None
    fle_encrypted_fields: str | None = None
    c_port: int | None = None
    time_to_first_byte: float | None = None
    x_edge_detailed_result_type: str | None = None
    sc_content_type: str | None = None
    sc_content_len: int | None = None
    sc_range_start: int | None = None
    sc_range_end: int | None = None

    @property
    def timestamp(self) -> datetime.datetime:
        """return the datetime representation."""
        return datetime.datetime.combine(
            self.date or datetime.date.min, self.time or datetime.time.min, datetime.timezone.utc
        )


def _to_datetime(value: str) -> datetime.datetime:
    """convert str to datetime."""
    return datetime.datetime.fromisoformat(value.rstrip("Z")).replace(tzinfo=datetime.timezone.utc)


def _to_cookie(value: str) -> dict[str, str]:
    """convert str to dictionary."""
    cookie = cookies.SimpleCookie()
    cookie.load(rawdata=value)
    return {urllib.parse.unquote(key): morsel.value for key, morsel in cookie.items()}


def _to_object(value: str, field: Field):  # noqa: C901 # pylint: disable=too-many-return-statements
    """convert str to python object."""
    value = value.strip('"')
    field_type = field.type.partition("|")[0].strip()

    if value == "-":
        return None
    if field.name == "cs_uri_stem":
        return urllib.parse.unquote(urllib.parse.unquote(value))
    if field.name == "cs_user_agent":
        return urllib.parse.unquote(value)
    if field.name == "cs_uri_query":
        return urllib.parse.parse_qs(value)
    if field.name == "cs_cookie":
        return _to_cookie(value)
    if field_type == "str":
        return value
    if field_type == "int":
        return int(value)
    if field_type == "float":
        return float(value)
    if field_type == "datetime.datetime":
        return _to_datetime(value)
    if field_type == "datetime.date":
        return datetime.date.fromisoformat(value)
    if field_type == "datetime.time":
        return datetime.time.fromisoformat(value).replace(tzinfo=datetime.timezone.utc)
    if field_type == "list[str]":
        return value.split(",")
    raise ValueError(f"unhandled value:type {value}:{field_type}")


# Function to parse CloudFront log file (supports .gz files)
def parse_cloudfront_log(file_path: Path) -> Generator[CloudFrontLogEntry, Any, None]:
    """
    Parse CloudFront log.

    file_path is the gz log file.

    :param file_path: the path of cloudfront log file, compressed by gzip
    :type file_path: Path
    :return: generator of log entries
    :rtype: CloudFrontLogEntry
    :raises Exception: if file_path does not exist, not a file
    """

    model_fields = fields(CloudFrontLogEntry)
    # Open and read .gz files
    with gzip.open(file_path, "rt", encoding="utf-8") as file:  # 'rt' mode for reading text
        for line in file:
            # Skip comments or empty lines
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            # Split the line into columns
            col = line.split("\t")

            yield CloudFrontLogEntry(
                *[_to_object(value, field) for value, field in zip(col, model_fields)]  # type: ignore[valid-type]
            )


def webpage_timebucket(t: datetime.datetime) -> datetime.datetime:
    """Put timestamp in 4 time buckets (6-hour interval).

    This function takes a datetime object and return the containing timebucket.
    The resulting datetime will have the hour set to 0, 6, 12, or 18, with minutes, seconds,
    and microseconds set to 0, and the timezone set to UTC.

    :param t: The original timestamp.
    :type t: datetime.datetime
    :return: The timestamp reprenting the containing timebucket (6-hour interval).
    :rtype: datetime.datetime
    """
    return t.replace(hour=t.hour // 6 * 6, second=0, microsecond=0, minute=0, tzinfo=datetime.timezone.utc)
