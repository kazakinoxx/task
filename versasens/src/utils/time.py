"""Module for time-related utility functions."""

import datetime

from src.utils.constants import LOCAL_TIMEZONE


def get_now() -> datetime.datetime:
    """
    Get the current time in the local timezone.

    Returns:
        The current time.

    """
    return datetime.datetime.now(tz=datetime.UTC).astimezone()


def datetime_to_tz_aware(
    dt: datetime.datetime,
) -> datetime.datetime:
    """
    Convert a datetime to a timezone-aware datetime.

    Args:
        dt: The datetime to convert

    Returns:
        The timezone-aware datetime.

    """
    return dt.replace(tzinfo=LOCAL_TIMEZONE)
