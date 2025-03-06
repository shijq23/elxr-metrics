################################################################################
# Copyright (c) 2024 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
################################################################################
from __future__ import annotations

import datetime
import gzip
from pathlib import Path

import pytest

from elxr_metrics.cloudfront_log import (
    CloudFrontLogEntry,
    _to_datetime,
    _to_object,
    parse_cloudfront_log,
    webpage_timebucket,
)


@pytest.mark.parametrize(
    "value, field, result",
    [
        # Existing cases
        (
            "/elxr/pool/main/g/gcc-12/libstdc%2b%2b6_12.2.0-14_amd64.deb",
            CloudFrontLogEntry.__dataclass_fields__["cs_uri_stem"],
            "/elxr/pool/main/g/gcc-12/libstdc++6_12.2.0-14_amd64.deb",
        ),
        # Date field
        (
            "2024-01-01",
            CloudFrontLogEntry.__dataclass_fields__["date"],
            datetime.date(2024, 1, 1),
        ),
        # Time field
        (
            "12:34:56",
            CloudFrontLogEntry.__dataclass_fields__["time"],
            datetime.time(12, 34, 56, tzinfo=datetime.timezone.utc),
        ),
        # Other fields
        (
            "200",
            CloudFrontLogEntry.__dataclass_fields__["sc_status"],
            200,
        ),
        (
            "1.23",
            CloudFrontLogEntry.__dataclass_fields__["time_taken"],
            1.23,
        ),
        (
            "key1=val1&key2=val2",
            CloudFrontLogEntry.__dataclass_fields__["cs_uri_query"],
            {"key1": ["val1"], "key2": ["val2"]},
        ),
        (
            "User-Agent=Mozilla",
            CloudFrontLogEntry.__dataclass_fields__["cs_cookie"],
            {"User-Agent": "Mozilla"},
        ),
        (
            "-",
            CloudFrontLogEntry.__dataclass_fields__["cs_method"],
            None,
        ),
    ],
)
def test_to_object(value, field, result):
    actual = _to_object(value, field)
    assert actual == result


def test_timestamp_property():
    """Test the timestamp property of CloudFrontLogEntry"""
    entry = CloudFrontLogEntry(
        date=datetime.date(2024, 1, 1), time=datetime.time(12, 34, 56, tzinfo=datetime.timezone.utc)
    )
    expected = datetime.datetime(2024, 1, 1, 12, 34, 56, tzinfo=datetime.timezone.utc)
    assert entry.timestamp == expected


def test_timestamp_property_with_none():
    """Test the timestamp property with None values"""
    entry = CloudFrontLogEntry()  # All fields None
    expected = datetime.datetime.combine(datetime.date.min, datetime.time.min, datetime.timezone.utc)
    assert entry.timestamp == expected


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


@pytest.mark.parametrize(
    "input_time, expected_bucket",
    [
        (
            datetime.datetime(2024, 1, 1, 1, 30, 45),
            datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
        ),
        (
            datetime.datetime(2024, 1, 1, 7, 30, 45),
            datetime.datetime(2024, 1, 1, 6, 0, 0, tzinfo=datetime.timezone.utc),
        ),
        (
            datetime.datetime(2024, 1, 1, 13, 30, 45),
            datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        ),
        (
            datetime.datetime(2024, 1, 1, 19, 30, 45),
            datetime.datetime(2024, 1, 1, 18, 0, 0, tzinfo=datetime.timezone.utc),
        ),
    ],
)
def test_webpage_timebucket(input_time, expected_bucket):
    """Test webpage_timebucket function"""
    result = webpage_timebucket(input_time)
    assert result == expected_bucket


def test_parse_log_file_not_found():
    """Test parsing non-existent log file"""
    with pytest.raises(FileNotFoundError):
        list(parse_cloudfront_log(Path("non_existent.gz")))


def test_parse_log_invalid_format(tmp_path):
    """Test parsing invalid log format"""
    log_file = tmp_path / "invalid.gz"
    with gzip.open(log_file, "wt") as f:
        f.write("invalid\nlog\nformat\n")

    with pytest.raises(ValueError):
        list(parse_cloudfront_log(log_file))


def test_parse_log_empty_file(tmp_path):
    """Test parsing empty log file"""
    log_file = tmp_path / "empty.gz"
    with gzip.open(log_file, "wt") as f:
        f.write("")

    entries = list(parse_cloudfront_log(log_file))
    assert len(entries) == 0


@pytest.mark.parametrize(
    "input_str, expected_datetime",
    [
        ("2024-01-01T12:34:56", datetime.datetime(2024, 1, 1, 12, 34, 56, tzinfo=datetime.timezone.utc)),
        ("2024-01-01T12:34:56Z", datetime.datetime(2024, 1, 1, 12, 34, 56, tzinfo=datetime.timezone.utc)),
        ("2024-01-01T00:00:00", datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)),
        ("2024-12-31T23:59:59Z", datetime.datetime(2024, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)),
        ("2024-02-29T15:30:45", datetime.datetime(2024, 2, 29, 15, 30, 45, tzinfo=datetime.timezone.utc)),  # Leap year
    ],
)
def test_to_datetime(input_str, expected_datetime):
    """Test _to_datetime function with various datetime strings"""
    result = _to_datetime(input_str)
    assert result == expected_datetime
    assert result.tzinfo == datetime.timezone.utc  # Ensure timezone is always UTC


def test_to_datetime_invalid_format():
    """Test _to_datetime function with invalid format"""
    with pytest.raises(ValueError):
        _to_datetime("invalid-date-format")


@pytest.mark.parametrize(
    "value, expected_datetime",
    [
        ("2024-01-01T12:34:56", datetime.datetime(2024, 1, 1, 12, 34, 56, tzinfo=datetime.timezone.utc)),
        ("2024-01-01T12:34:56Z", datetime.datetime(2024, 1, 1, 12, 34, 56, tzinfo=datetime.timezone.utc)),
        ('"2024-01-01T00:00:00"', datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)),  # With quotes
        ("-", None),  # Empty value marker
    ],
)
def test_to_object_datetime(value, expected_datetime):
    """Test _to_object function with datetime field type"""
    # Create a mock Field object with datetime.datetime type
    mock_field = CloudFrontLogEntry.__dataclass_fields__["date"]  # Use existing field
    object.__setattr__(mock_field, "type", "datetime.datetime | None")  # Override type

    result = _to_object(value, mock_field)
    assert result == expected_datetime
    if result is not None:
        assert result.tzinfo == datetime.timezone.utc


def test_to_object_datetime_invalid():
    """Test _to_object function with invalid datetime values"""
    mock_field = CloudFrontLogEntry.__dataclass_fields__["date"]
    object.__setattr__(mock_field, "type", "datetime.datetime | None")

    invalid_values = [
        "invalid-datetime",
        "2024-13-01T12:34:56",  # Invalid month
        "2024-01-32T12:34:56",  # Invalid day
        "2024-01-01T25:00:00",  # Invalid hour
        "",  # Empty string
        # "2024-01-01",  # Missing time component
    ]

    for invalid_value in invalid_values:
        with pytest.raises(ValueError):
            _to_object(invalid_value, mock_field)


@pytest.fixture
def list_str_field():
    """Fixture to temporarily modify field type and restore it after test"""
    mock_field = CloudFrontLogEntry.__dataclass_fields__["date"]
    original_type = mock_field.type
    object.__setattr__(mock_field, "type", "list[str]")
    yield mock_field
    object.__setattr__(mock_field, "type", original_type)


@pytest.mark.parametrize(
    "value, expected_list",
    [
        ("item1,item2,item3", ["item1", "item2", "item3"]),
        ("single", ["single"]),
        ("item1,,item3", ["item1", "", "item3"]),  # Empty middle item
        ("", [""]),  # Empty string
        ("spaces, with spaces ,no spaces", ["spaces", " with spaces ", "no spaces"]),  # Spaces in values
        ("special,chars!,@#$%", ["special", "chars!", "@#$%"]),  # Special characters
        # ('quoted,"comma,inside",normal', ["quoted", '"comma,inside"', "normal"]),  # Quoted values
        ("-", None),  # Empty value marker
    ],
)
def test_to_object_list_str(list_str_field, value, expected_list):
    """Test _to_object function with list[str] field type"""
    result = _to_object(value, list_str_field)
    assert result == expected_list


def test_to_object_list_str_edge_cases(list_str_field):
    """Test _to_object function with list[str] field type edge cases"""
    # Test trailing comma
    assert _to_object("item1,item2,", list_str_field) == ["item1", "item2", ""]

    # Test leading comma
    assert _to_object(",item1,item2", list_str_field) == ["", "item1", "item2"]

    # Test multiple consecutive commas
    assert _to_object("item1,,,item2", list_str_field) == ["item1", "", "", "item2"]

    # Test whitespace only items
    assert _to_object("  ,\t,\n", list_str_field) == ["  ", "\t", "\n"]


def test_to_object_list_str_unicode(list_str_field):
    """Test _to_object function with list[str] field type and unicode characters"""
    # Test unicode characters
    test_cases = [
        ("español,русский,日本語", ["español", "русский", "日本語"]),
        ("emoji🎉,symbols™,accents é", ["emoji🎉", "symbols™", "accents é"]),
        ("mixed,ascii,привет", ["mixed", "ascii", "привет"]),
    ]

    for input_value, expected in test_cases:
        result = _to_object(input_value, list_str_field)
        assert result == expected


def test_to_object_list_str_long_values(list_str_field):
    """Test _to_object function with list[str] field type and long values"""
    # Test long strings
    long_string = "x" * 1000
    value = f"short,{long_string},medium"
    result = _to_object(value, list_str_field)

    assert len(result) == 3
    assert result[0] == "short"
    assert result[1] == long_string
    assert result[2] == "medium"
    assert len(result[1]) == 1000
