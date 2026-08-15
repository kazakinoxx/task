"""Tests for time-related utility functions."""

import datetime

import pytest

from src.utils.constants import LOCAL_TIMEZONE
from src.utils.time import datetime_to_tz_aware, get_now


class TestGetNow:
    def test_returns_datetime(self):
        result = get_now()

        assert isinstance(result, datetime.datetime)

    def test_has_timezone(self):
        result = get_now()

        assert result.tzinfo is not None

    def test_is_local_timezone(self):
        result = get_now()

        assert result.tzinfo == LOCAL_TIMEZONE

    def test_is_approximately_current_time(self):
        result = get_now()
        expected = datetime.datetime.now(tz=datetime.UTC).astimezone()

        # Check within 1 second
        diff = abs((result - expected).total_seconds())
        assert diff < 1.0


class TestDatetimeToTzAware:
    def test_adds_timezone_to_naive_datetime(self):
        dt = datetime.datetime(2025, 10, 25, 15, 30, 45)
        result = datetime_to_tz_aware(dt)

        assert result.tzinfo == LOCAL_TIMEZONE
        assert result.year == 2025
        assert result.month == 10
        assert result.day == 25
        assert result.hour == 15
        assert result.minute == 30
        assert result.second == 45

    def test_preserves_existing_timezone(self):
        dt = datetime.datetime(2025, 10, 25, 15, 30, 45, tzinfo=LOCAL_TIMEZONE)
        result = datetime_to_tz_aware(dt)

        assert result.tzinfo == LOCAL_TIMEZONE
        assert result == dt

    def test_works_with_microseconds(self):
        dt = datetime.datetime(2025, 10, 25, 15, 30, 45, 123456)
        result = datetime_to_tz_aware(dt)

        assert result.tzinfo == LOCAL_TIMEZONE
        assert result.microsecond == 123456

    def test_does_not_convert_timezone(self):
        # Create datetime with a different timezone
        utc_tz = datetime.timezone.utc
        dt = datetime.datetime(2025, 10, 25, 15, 30, 45, tzinfo=utc_tz)
        result = datetime_to_tz_aware(dt)

        # Should replace timezone, not convert
        assert result.tzinfo == LOCAL_TIMEZONE
        assert result.hour == 15  # Hour should remain the same
        assert result.minute == 30