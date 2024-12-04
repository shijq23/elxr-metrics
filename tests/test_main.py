################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
from __future__ import annotations

import stat
import sys
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import elxr_metrics.__main__
from elxr_metrics.__main__ import is_dir, is_file, main


@pytest.mark.parametrize(
    "path, val",
    [
        (".", "."),
        ("tests/", "tests/"),
        ("/", "/"),
    ],
)
def test_is_dir(path, val):
    actual = is_dir(ArgumentParser(), path)
    assert actual == Path(val)


@pytest.mark.parametrize(
    "path",
    [
        ("~/"),
        ("README.md"),
        ("zzz/"),
        (""),
        (None),
    ],
)
def test_is_dir_error(path):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        is_dir(ArgumentParser(), path)
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 2


@pytest.mark.parametrize(
    "path, val",
    [
        (__file__, __file__),
        (
            "tests/logs/elxr_org/A65ZZCR5KMGAR8.2024-10-01-18.2d243ee0.gz",
            "tests/logs/elxr_org/A65ZZCR5KMGAR8.2024-10-01-18.2d243ee0.gz",
        ),
        ("zzzzz.zzz", "zzzzz.zzz"),
    ],
)
def test_is_file(path, val):
    actual = is_file(ArgumentParser(), path)
    assert actual == Path(val)


@pytest.mark.parametrize(
    "path",
    [
        (""),
        (None),
        ("."),
        ("tests/logs/"),
    ],
)
def test_is_file_error(path):
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        is_file(ArgumentParser(), path)
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 2


@pytest.mark.parametrize(
    "mode",
    [
        (stat.S_IWUSR),  # Writable only
        (stat.S_IRUSR),  # Readable only
    ],
)
@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason="Windows only supports setting the file’s read-only flag",
)
def test_is_file_mode(tmp_path, mode):
    p = tmp_path / "hello.csv"
    p.touch()
    p.chmod(mode)
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        is_file(ArgumentParser(), p)
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 2


def test_main_elxr_org_view(tmp_path):
    """test main function to parse elxr org view"""
    csv_file = tmp_path / "test.csv"
    log = Path("tests/logs/elxr_org")
    elxr_metrics.__main__.parse_elxr_org_logs = MagicMock()
    main([str(log), str(csv_file), "elxr_org_view"])
    elxr_metrics.__main__.parse_elxr_org_logs.assert_called_once_with(log, csv_file)


def test_main_mirror_elxr_dev(tmp_path):
    """test main function to parse package download"""
    csv_file = tmp_path / "test.csv"
    log = Path("tests/logs/mirror_elxr_dev")
    elxr_metrics.__main__.parse_mirror_elxr_dev_logs = MagicMock()
    main([str(log), str(csv_file), "package_download"])
    elxr_metrics.__main__.parse_mirror_elxr_dev_logs.assert_called_once_with(log, csv_file)


def test_main_downloads_elxr_dev(tmp_path):
    """test main function to parse image download"""
    csv_file = tmp_path / "test.csv"
    log = Path("tests/logs/downloads_elxr_dev")
    elxr_metrics.__main__.parse_downloads_elxr_dev_logs = MagicMock()
    main([str(log), str(csv_file), "image_download"])
    elxr_metrics.__main__.parse_downloads_elxr_dev_logs.assert_called_once_with(log, csv_file)


def test_main_log_type(tmp_path):
    """test main function with wrong log_type"""
    csv_file = tmp_path / "test.csv"
    log = Path("tests/logs/mirror_elxr_dev")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        main([str(log), str(csv_file), "wrong_log_type"])
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 2


@pytest.mark.parametrize(
    "arg",
    [
        ([sys.argv[0]]),
        ([sys.argv[0], "tests/logs/elxr_org"]),
        ([sys.argv[0], "tests/logs/elxr_org", "tests/logs/a.csv"]),
    ],
)
def test_main_none(monkeypatch, arg):
    """test main function with no argument"""
    with monkeypatch.context() as m, pytest.raises(SystemExit) as pytest_wrapped_e:
        m.setattr(sys, "argv", arg)
        main()
    assert pytest_wrapped_e.type is SystemExit
    assert pytest_wrapped_e.value.code == 2
