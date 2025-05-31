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
from contextlib import contextmanager
from functools import cache
from pathlib import Path

import duckdb

from elxr_metrics.cloudfront_log import CloudFrontLogEntry, parse_cloudfront_log
from elxr_metrics.elapsed import timing

MIRROR_ELXR_DEV_CSV = Path("public/package_stats.csv")

logger = logging.getLogger(__name__)


@contextmanager
def _popular_package(csv_file: Path):
    """
    load and save new package download into csv_file.
    package_top_10.csv is also updated at the save folder.
    """
    top_10 = csv_file.parent / "package_top_10.csv"
    conn = duckdb.connect(":memory:")
    try:
        conn.execute("""DROP TABLE IF EXISTS stats;""")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
            Name VARCHAR PRIMARY KEY,
            Download INTEGER
        );"""
        )
        if not csv_file.exists():  # create if not exist
            conn.execute(
                f"""
                COPY (SELECT * FROM stats LIMIT 0)
                TO '{csv_file}'
                WITH (FORMAT CSV, DELIMITER ',', HEADER, NEW_LINE e'\n');"""
            )
        if csv_file.stat().st_size > 13:  # expect header "Name,Download"
            conn.execute(
                f"""
                COPY stats
                FROM '{csv_file}'
                WITH (FORMAT CSV, DELIMITER ',', HEADER);"""
            )
        yield conn
    finally:
        conn.execute(
            f"""
            COPY (SELECT * FROM stats ORDER BY Download DESC, Name ASC)
            TO '{csv_file}'
            WITH (FORMAT CSV, DELIMITER ',', HEADER, NEW_LINE e'\n');"""
        )
        conn.execute(
            f"""
            COPY (SELECT * FROM stats ORDER BY Download DESC, Name ASC LIMIT 10)
            TO '{top_10}'
            WITH (FORMAT CSV, DELIMITER ',', HEADER, NEW_LINE e'\n');"""
        )
        conn.close()


# _DEB_NAME_RE = re.compile(r"^([a-zA-Z0-9\-\+\.]+)_(.+?)_(.+?).deb$", re.ASCII)
_DEB_NAME_RE = re.compile(r"^([a-zA-Z0-9\-\+\.]+)_", re.ASCII)


@cache
def _parse_deb_name(path: str) -> str | None:
    """
    Extract package name from a given URI path.

    Parameters:
    path (str): The URI path from which to extract the package name.

    Returns:
    str | None: The extracted package name if successful, otherwise None.

    Purpose:
    This function takes a URI path as input, extracts the file name from it, and attempts to parse the package name
    from the file name using a regular expression. If successful, it returns the package name; otherwise, it logs a
    warning and returns None.

    Notes:
    The function uses a regular expression to match the package name in the file name. The regular expression is
    defined as _DEB_NAME_RE and matches one or more alphanumeric characters, hyphens, plus signs, or dots at the
    beginning of the file name. If the match is successful, the function returns the matched package name; otherwise,
    it logs a warning and returns None.
    """
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
    """
    Updates the package download count in the database based on the provided CloudFront log entry.

    Parameters:
    conn (duckdb.DuckDBPyConnection): The connection to the DuckDB database.
    log_entry (CloudFrontLogEntry): The CloudFront log entry containing information about the package download.

    Returns:
    None

    Notes:
    This function assumes that the database connection is already established and the stats table exists.
    The function uses the _parse_deb_name function to extract the package name from the log entry's URI stem.
    """
    if log_entry.sc_content_type not in (
        "application/vnd.debian.binary-package",
        "binary/octet-stream",
    ):  # only count deb file
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
        f"""
        INSERT INTO stats (Name, Download) values ('{name}', 1)
        ON CONFLICT (Name) DO UPDATE SET Download = stats.Download + 1; """
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
    with _popular_package(csv_file) as conn:
        conn.execute("BEGIN TRANSACTION;")
        for child in log_folder.glob("*.gz"):
            for entry in parse_cloudfront_log(child):
                _update_package_download(conn, entry)
        conn.execute("COMMIT;")
