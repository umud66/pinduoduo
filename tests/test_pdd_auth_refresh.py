from datetime import datetime, timedelta
from app.services.pdd.auth_lifecycle import token_refresh_action

def test_no_expiry_field_does_not_guess_refresh_time() -> None:
    now = datetime(2026, 8, 18, 12, 0)
    assert token_refresh_action(now=now, access_expires_at=None, refresh_expires_at=None, has_refresh_token=True) == "none"

def test_refreshes_before_access_expiry_when_refresh_token_exists() -> None:
    now = datetime(2026, 8, 18, 12, 0)
    assert token_refresh_action(
        now=now,
        access_expires_at=now + timedelta(minutes=20),
        refresh_expires_at=now + timedelta(days=5),
        has_refresh_token=True,
    ) == "refresh"

def test_requires_reauthorization_when_refresh_token_is_expired() -> None:
    now = datetime(2026, 8, 18, 12, 0)
    assert token_refresh_action(
        now=now,
        access_expires_at=now + timedelta(minutes=5),
        refresh_expires_at=now - timedelta(seconds=1),
        has_refresh_token=True,
    ) == "reauthorize"

def test_does_not_refresh_healthy_token() -> None:
    now = datetime(2026, 8, 18, 12, 0)
    assert token_refresh_action(
        now=now,
        access_expires_at=now + timedelta(hours=3),
        refresh_expires_at=now + timedelta(days=5),
        has_refresh_token=True,
    ) == "none"
