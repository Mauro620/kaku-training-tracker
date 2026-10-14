"""Fecha local del usuario. Un solo lugar para que `hoy` no dependa de la zona
horaria del servidor (la app guarda fechas locales, ver `settings.tz`)."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def hoy_local() -> date:
    return datetime.now(ZoneInfo(get_settings().tz)).date()
