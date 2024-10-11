################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""module to parse elxr.org logs and save web page view count"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import duckdb
from duckdb import DuckDBPyConnection

from elxr_metrics.cloudfront_log import CloudFrontLogEntry, parse_cloudfront_log, webpage_timebucket
from elxr_metrics.elapsed import timing

ELXR_ORG_VIEW_CSV = Path("public/elxr_org_view.csv")


@contextmanager
def _trend(csv_file: Path) -> Generator[DuckDBPyConnection, Any, None]:
    conn = duckdb.connect(":memory:")
    try:
        conn.execute("""DROP TABLE IF EXISTS trend;""")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trend (
            TimeBucket TIMESTAMP PRIMARY KEY,
            ViewCount INTEGER
        );"""
        )
        if not csv_file.exists():
            conn.execute(
                f"""
                COPY (SELECT * FROM trend LIMIT 0)
                TO '{csv_file}'
                WITH (FORMAT CSV, DELIMITER ',', HEADER, NEW_LINE e'\n');"""
            )
        if csv_file.stat().st_size > 12:  # expect header
            conn.execute(
                f"""
                COPY trend
                FROM '{csv_file}'
                WITH (FORMAT CSV, DELIMITER ',', HEADER);"""
            )
        yield conn
    finally:
        conn.execute(
            f"""
            COPY (SELECT * FROM trend WHERE TimeBucket + INTERVAL 732 DAY > CURRENT_TIMESTAMP ORDER BY TimeBucket ASC)
            TO '{csv_file}'
            WITH (FORMAT CSV, DELIMITER ',', HEADER, NEW_LINE e'\n');"""
        )
        conn.close()


def _update_elxr_org(conn: DuckDBPyConnection, log_entry: CloudFrontLogEntry) -> None:
    if log_entry.sc_content_type != "text/html":  # only count web page reviews
        return
    t = webpage_timebucket(log_entry.timestamp)
    ts = t.strftime(r"%Y-%m-%d %H:%M:%S")
    conn.execute(
        f" \
        INSERT INTO trend (TimeBucket, ViewCount) values ('{ts}', 1) \
        ON CONFLICT (TimeBucket) DO UPDATE SET ViewCount = trend.ViewCount + 1; "
    )


@timing
def parse_elxr_org_logs(log_folder: Path, csv_file: Path = ELXR_ORG_VIEW_CSV):
    """
    parse cloudfront log files and populate page view count into database.

    :param log_folder: the parent folder path of log files (compressed by gzip)
    :type log_folder: Path
    :param csv_file: the path of CSV file, default to ELXR_ORG_VIEW_CSV
    :type csv_file: Path
    :return: None
    :raises Exception: if log_folder does not exist, not a directory.
                       if csv_file is not a file
    """
    with _trend(csv_file) as conn:
        conn.execute("BEGIN TRANSACTION;")
        for child in log_folder.glob("*.gz"):
            for entry in parse_cloudfront_log(child):
                _update_elxr_org(conn, entry)
        conn.execute("COMMIT;")
