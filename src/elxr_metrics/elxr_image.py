################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""module to parse downloads.elxr.dev logs and update image download count"""

from __future__ import annotations

import logging
import re
#from contextlib import contextmanager # No longer needed directly here
from functools import cache
from pathlib import Path

import duckdb # Still needed for DuckDBPyConnection type hint if _update_image_download is strict

from elxr_metrics.cloudfront_log import CloudFrontLogEntry, parse_cloudfront_log
from elxr_metrics.elapsed import timing
from .db_utils import manage_db_connection # Import the new utility

DOWNLOADS_ELXR_DEV_CSV = Path("public/image_stats.csv")

logger = logging.getLogger(__name__)


# _popular_image context manager is removed.

_IMAGE_NAME_RE = re.compile(r"elxr-.+\.(img\.zst|tar\.gz|img|iso)$", re.ASCII)


@cache
def _parse_image_name(path: str) -> str | None:
    """Extract image name from uri path"""
    #
    assert path
    file_name = Path(path).name
    if _IMAGE_NAME_RE.search(file_name):
        # If there's a match, remove the extension and return the result
        return file_name
        # return _IMAGE_NAME_RE.sub("", file_name)

    # If no match is found, return None
    return None


def _update_image_download(conn: duckdb.DuckDBPyConnection, log_entry: CloudFrontLogEntry) -> None:
    if log_entry.sc_content_type is None or not log_entry.sc_content_type.startswith("application/"):
        # application/x-iso9660-image (iso)
        # application/zstd (zst)
        # application/x-tar (tar.gz)
        # application/octet-stream (img)
        # application/gzip (tar.gz)
        return
    if log_entry.sc_status is None or log_entry.sc_status >= 400:
        return
    if log_entry.x_edge_result_type is None or log_entry.x_edge_result_type in (
        "LimitExceeded",
        "CapacityExceeded",
        "Error",
    ):
        return
    if log_entry.sc_bytes is None or log_entry.sc_bytes < 500000:
        # set the minimum image size 500KB
        return
    if log_entry.cs_uri_stem is None:
        return
    name = _parse_image_name(log_entry.cs_uri_stem)
    if not name:
        return
    conn.execute(
        """
        INSERT INTO images (Name, Download) values (?, 1)
        ON CONFLICT (Name) DO UPDATE SET Download = images.Download + 1; """,
        [name]
    )


@timing
def parse_downloads_elxr_dev_logs(log_folder: Path, csv_file: Path = DOWNLOADS_ELXR_DEV_CSV) -> None:
    """parse logs from downloads.elxr.dev site and extract image download count

    :param log_folder: the parent folder path of log files (compressed by gzip)
    :type log_folder: Path
    :param csv_file: the path of CSV file, default to DOWNLOADS_ELXR_DEV_CSV
    :type csv_file: Path
    :return: None
    :raises Exception: if log_folder does not exist, not a directory.
                       if csv_file is not a file"""
    table_name = "images"
    table_schema = "Name VARCHAR PRIMARY KEY, Download INTEGER"
    top_n_csv_path = csv_file.parent / "image_top_10.csv"

    with manage_db_connection(
        db_name=":memory:",
        table_name=table_name,
        table_schema=table_schema,
        input_csv_path=str(csv_file),
        output_csv_path=str(csv_file),
        top_n_csv_path=str(top_n_csv_path),
        top_n=10,
    ) as conn:
        conn.execute("BEGIN TRANSACTION;")
        for child in log_folder.glob("*.gz"):
            for entry in parse_cloudfront_log(child):
                _update_image_download(conn, entry)
        conn.execute("COMMIT;")
