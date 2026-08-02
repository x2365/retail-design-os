"""Работа со временем. Инвариант: все даты/время в БД — datetime в UTC."""

from __future__ import annotations

import datetime as dt


def to_utc_datetime(value: dt.date | dt.datetime | None) -> dt.datetime | None:
    """Приводит вход к timezone-aware datetime в UTC.

    - None → None
    - datetime без tz → считаем, что это UTC
    - datetime с tz → переводим в UTC
    - date → полночь UTC этого дня
    """
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)
    return dt.datetime(value.year, value.month, value.day, tzinfo=dt.UTC)
