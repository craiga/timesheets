"""Stuff for dealing with datetimes."""

from datetime import UTC, datetime

TIMEZONE = datetime.now(UTC).astimezone().tzinfo


def round_to_nearest_five_minutes(dt: datetime) -> datetime:
    """Round to the nearest five minutes."""
    return datetime.fromtimestamp(round(dt.timestamp() / 300) * 300, tz=dt.tzinfo)
