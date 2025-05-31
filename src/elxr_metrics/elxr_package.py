################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""module to parse mirror.elxr.dev logs and update package download count"""

from __future__ import annotations

import logging
import re
#from contextlib import contextmanager # No longer needed directly here
from functools import cache
from pathlib import Path

import duckdb # Still needed for DuckDBPyConnection type hint

from elxr_metrics.cloudfront_log import CloudFrontLogEntry, parse_cloudfront_log
from elxr_metrics.elapsed import timing
from .db_utils import manage_db_connection # Import the new utility

MIRROR_ELXR_DEV_CSV = Path("public/package_stats.csv")

logger = logging.getLogger(__name__)


# _popular_package context manager is removed.


# _DEB_NAME_RE = re.compile(r"^([a-zA-Z0-9\-\+\.]+)_(.+?)_(.+?).deb$", re.ASCII)
_DEB_NAME_RE = re.compile(r"^([a-zA-Z0-9\-\+\.]+)_", re.ASCII)


@cache
def _parse_deb_name(path: str) -> str | None:
    """Extract package name from uri path"""
    # get src package name in stead of binary
    # apt-get showsrc file.deb
    # apt-get search name
    # https://mirror.elxr.dev/elxr/dists/aria/main/binary-amd64/Packages
    # https://debian.osuosl.org/debian/indices/package-file.map.bz2
    assert path
    file_name = Path(path).name
    match = _DEB_NAME_RE.match(file_name)
    if match:
        return match.group(1)
    logger.warning("failed to parse deb package name from: {%s}", path)
    return None


def _update_package_download(conn: duckdb.DuckDBPyConnection, log_entry: CloudFrontLogEntry) -> None:
    if log_entry.sc_content_type != "application/vnd.debian.binary-package":  # only count deb file
        return
    if log_entry.sc_status is None or log_entry.sc_status >= 400:
        return
    if log_entry.cs_uri_stem is None or not log_entry.cs_uri_stem.startswith("/elxr/pool/"):
        return
    if not log_entry.cs_uri_stem.endswith(".deb"):
        return
    name = _parse_deb_name(log_entry.cs_uri_stem)
    if not name:
        return
    conn.execute(
        """
        INSERT INTO stats (Name, Download) values (?, 1)
        ON CONFLICT (Name) DO UPDATE SET Download = stats.Download + 1; """,
        [name]
    )


@timing
def parse_mirror_elxr_dev_logs(log_folder: Path, csv_file: Path = MIRROR_ELXR_DEV_CSV) -> None:
    """parse logs from mirror site and extract package download count

    :param log_folder: the parent folder path of log files (compressed by gzip)
    :type log_folder: Path
    :param csv_file: the path of CSV file, default to MIRROR_ELXR_DEV_CSV
    :type csv_file: Path
    :return: None
    :raises Exception: if log_folder does not exist, not a directory.
                       if csv_file is not a file"""
    table_name = "stats" # As used in the original _update_package_download
    table_schema = "Name VARCHAR PRIMARY KEY, Download INTEGER" # Restored PRIMARY KEY
    top_n_csv_path = csv_file.parent / "package_top_10.csv"

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
                _update_package_download(conn, entry)
        conn.execute("COMMIT;")
