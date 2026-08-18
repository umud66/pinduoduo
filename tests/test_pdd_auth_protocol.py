from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from app.services.pdd.auth_protocol import build_shop_authorization_url, parse_token_payload

def test_build_shop_authorization_url_preserves_state_and_redirect() -> None:
    url = build_shop_authorization_url(
        client_id="client-1",
        redirect_uri="http://127.0.0.1:8765/api/pdd/oauth/callback",
        state="state-abc",
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert parsed.netloc == "fuwu.pinduoduo.com"
    assert qs["client_id"] == ["client-1"]
    assert qs["response_type"] == ["code"]
    assert qs["state"] == ["state-abc"]
    assert qs["redirect_uri"] == ["http://127.0.0.1:8765/api/pdd/oauth/callback"]

def test_parse_create_token_payload_uses_platform_expiry_fields() -> None:
    result = parse_token_payload({
        "pop_auth_token_create_response": {
            "owner_id": 123,
            "owner_name": "测试店铺",
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": 1_800_000_000,
            "refresh_token_expires_at": 1_900_000_000,
            "scope": ["goods", "order"],
        }
    })
    assert result["owner_id"] == "123"
    assert result["owner_name"] == "测试店铺"
    assert result["scopes"] == ["goods", "order"]
    assert result["access_expires_at"] == datetime.fromtimestamp(1_800_000_000, timezone.utc).replace(tzinfo=None)

def test_parse_refresh_token_payload_supports_refresh_root() -> None:
    result = parse_token_payload({
        "pop_auth_token_refresh_response": {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "expires_in": 3600,
        }
    }, refresh=True)
    assert result["access_token"] == "new-access"
    assert result["refresh_token"] == "new-refresh"
    assert result["access_expires_at"] is not None

def test_parse_token_payload_rejects_missing_access_token() -> None:
    with pytest.raises(ValueError):
        parse_token_payload({"pop_auth_token_create_response": {}})
