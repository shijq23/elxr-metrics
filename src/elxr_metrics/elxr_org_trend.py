################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""module to parse elxr.org logs and save web page view count"""

from __future__ import annotations

from contextlib import contextmanager
from functools import cache
import logging
from pathlib import Path
from typing import Any, Generator

import duckdb
import maxminddb
from duckdb import DuckDBPyConnection

from elxr_metrics.cloudfront_log import CloudFrontLogEntry, parse_cloudfront_log, webpage_timebucket
from elxr_metrics.elapsed import timing

ELXR_ORG_VIEW_CSV = Path("public/elxr_org_view.csv")

logger = logging.getLogger(__name__)


@contextmanager
def _trend(csv_file: Path) -> Generator[DuckDBPyConnection, Any, None]:
    country_file = csv_file.parent / "country.csv"
    conn = duckdb.connect(":memory:")
    try:
        conn.execute("""DROP TABLE IF EXISTS trend;""")
        conn.execute("""DROP TABLE IF EXISTS temp_data;""")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trend (
            TimeBucket TIMESTAMP PRIMARY KEY,
            ViewCount INTEGER,
            UniqueUser INTEGER
        );"""
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS country (
            Code VARCHAR PRIMARY KEY,
            Name VARCHAR,
            Count INTEGER
        );"""
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS temp_data (
            TimeBucket TIMESTAMP,
            ClientIP VARCHAR
        );"""
        )
        if not csv_file.exists():
            conn.execute(
                f"""
                COPY (SELECT * FROM trend LIMIT 0)
                TO '{csv_file}'
                WITH (FORMAT CSV, DELIMITER ',', HEADER, NEW_LINE e'\n');"""
            )
        if csv_file.stat().st_size > 31:  # expect header "TimeBucket,ViewCount,UniqueUser"
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
        conn.execute(
            f"""
            COPY (SELECT * FROM country ORDER BY Count DESC, Code ASC)
            TO '{country_file}'
            WITH (FORMAT CSV, DELIMITER ',', HEADER, NEW_LINE e'\n');"""
        )
        conn.close()


def _merge_elxr_org(conn: DuckDBPyConnection) -> None:
    """merge collected temp data into trend table"""
    conn.execute(
        """
        INSERT INTO trend (TimeBucket, ViewCount, UniqueUser)
        SELECT
            TimeBucket,
            COUNT(*) AS ViewCount,
            COUNT(DISTINCT ClientIP) AS UniqueUser
        FROM temp_data
        GROUP BY TimeBucket
        ON CONFLICT (TimeBucket)
        DO UPDATE SET
            ViewCount = ViewCount + EXCLUDED.ViewCount,
            UniqueUser = UniqueUser + EXCLUDED.UniqueUser;
        """
    )


_COUNTRY_READER = maxminddb.open_database(r"GeoLite2-Country/GeoLite2-Country.mmdb")


@cache
def _country_lookup(ip: str) -> tuple[str, str]:
    """
    map IP address to country iso-code and name.

    :param ip: user IP address
    :type ip: str
    :return: country iso-code and name, or "N/A" if not found
    :rtype: tuple[str, str]
    """
    country = "N/A"
    code = "N/A"
    try:
        r = _COUNTRY_READER.get(ip)
        c = r.get("country") or r.get("registered_country")
        code = c["iso_code"]
        country = c["names"]["en"]
    except Exception:  # pylint: disable=broad-except
        pass
    if code == "N/A":
        logger.warning("failed to lookup country for IP: %s", ip)
    return code, country


def _process_log_entry(conn: DuckDBPyConnection, log_entry: CloudFrontLogEntry) -> None:
    """process the log entry and insert into temp table"""
    if log_entry.sc_content_type != "text/html":  # only count web page reviews
        return
    t = webpage_timebucket(log_entry.timestamp)
    ts = t.strftime(r"%Y-%m-%d %H:%M:%S")
    conn.execute(f"INSERT INTO temp_data (TimeBucket, ClientIP) values ('{ts}', '{log_entry.c_ip}');")
    code, name = _country_lookup(log_entry.c_ip)
    if code == "N/A":  # no country info, skip
        return
    conn.execute(
        f"""
        INSERT INTO country (Code, Name, Count) values ('{code}', '{name}', 1)
        ON CONFLICT (Code) DO UPDATE SET Count = country.Count + 1; """
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
                _process_log_entry(conn, entry)
        _merge_elxr_org(conn)
        conn.execute("COMMIT;")
