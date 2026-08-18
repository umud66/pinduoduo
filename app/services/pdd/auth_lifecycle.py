from __future__ import annotations

from datetime import datetime, timedelta

REFRESH_AHEAD_MINUTES = 30

def token_refresh_action(
    *,
    now: datetime,
    access_expires_at: datetime | None,
    refresh_expires_at: datetime | None,
    has_refresh_token: bool,
) -> str:
    if refresh_expires_at is not None and refresh_expires_at <= now:
        return "reauthorize"
    if access_expires_at is None:
        return "none"
    if access_expires_at > now + timedelta(minutes=REFRESH_AHEAD_MINUTES):
        return "none"
    if has_refresh_token:
        return "refresh"
    return "reauthorize"
