#!/usr/bin/env python3
################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
"""the package command line entrypoint"""

from __future__ import annotations

import argparse
import stat
import sys
from pathlib import Path

from elxr_metrics.elxr_image import parse_downloads_elxr_dev_logs
from elxr_metrics.elxr_org_trend import parse_elxr_org_logs
from elxr_metrics.elxr_package import parse_mirror_elxr_dev_logs


def is_dir(parser: argparse.ArgumentParser, path: str) -> Path:
    """check if path is a directory"""
    if not path:
        parser.error("The path is empty!")
    d = Path(path)
    if not d.exists():
        parser.error(f"The path does not exist! ({path})")
    elif not d.is_dir():
        parser.error(f"The path is not directory! ({path})")
    return d


def is_file(parser: argparse.ArgumentParser, path: str) -> Path:
    """check if path is a readable file"""
    if not path:
        parser.error("The path is empty!")
    d = Path(path)
    if not d.exists():
        return d
    if not d.is_file():
        parser.error(f"The path is not file! ({path})")
    elif not bool(d.stat().st_mode & stat.S_IRUSR):
        parser.error(f"The file is not readable! ({path})")
    elif not bool(d.stat().st_mode & stat.S_IWUSR):
        parser.error(f"The file is not writable! ({path})")
    return d


def main(args: list[str] | None = None) -> int:
    """
    The main routine to parse cloudfront logs and store into csv file.

    It requires 3 command line argument:
    log_path -- the log file directory
    csv_path -- the csv file to load and store
    log_type -- the log type, one of elxr_org_view, package_download, image_download
    """
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="parse CloudFront log files",
        epilog="Example: python3 %(prog)s ../logs/elxr_org ../public/elxr_org_view.csv elxr_org_view",
    )
    parser.add_argument(
        "log_path",
        nargs=1,
        type=lambda x: is_dir(parser, x),
        help="the directory contains log files",
    )
    parser.add_argument(
        "csv_path",
        nargs=1,
        type=lambda x: is_file(parser, x),
        help="the csv file to load and store",
    )
    parser.add_argument(
        "log_type",
        nargs=1,
        choices=["elxr_org_view", "package_download", "image_download"],
        help="the log type",
    )
    pa = parser.parse_args(args)

    log_path: Path = pa.log_path[0]
    csv_path: Path = pa.csv_path[0]
    log_type: str = pa.log_type[0]

    if log_type == "elxr_org_view":
        parse_elxr_org_logs(log_path, csv_path)
    elif log_type == "package_download":
        parse_mirror_elxr_dev_logs(log_path, csv_path)
    else:  # must be "image_download"
        parse_downloads_elxr_dev_logs(log_path, csv_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
