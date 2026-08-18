from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

DEFAULT_SHOP_AUTH_URL = "https://fuwu.pinduoduo.com/service-market/auth"

def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def build_shop_authorization_url(*, client_id: str, redirect_uri: str, state: str, auth_web_url: str = DEFAULT_SHOP_AUTH_URL) -> str:
    return f"{auth_web_url}?{urlencode({'client_id': client_id, 'response_type': 'code', 'redirect_uri': redirect_uri, 'state': state})}"

def _unix_time(value: Any, fallback_seconds: Any = None) -> datetime | None:
    try:
        timestamp = int(value or 0)
    except (TypeError, ValueError):
        timestamp = 0
    if timestamp > 0:
        return datetime.fromtimestamp(timestamp, timezone.utc).replace(tzinfo=None)
    try:
        seconds = int(fallback_seconds or 0)
    except (TypeError, ValueError):
        seconds = 0
    return utcnow_naive() + timedelta(seconds=seconds) if seconds > 0 else None

def parse_token_payload(payload: dict[str, Any], *, refresh: bool = False) -> dict[str, Any]:
    root_key = "pop_auth_token_refresh_response" if refresh else "pop_auth_token_create_response"
    data = payload.get(root_key)
    if not isinstance(data, dict):
        raise ValueError(f"PDD 授权响应缺少 {root_key}")
    token = str(data.get("access_token") or "").strip()
    if not token:
        raise ValueError("PDD 授权响应没有 access_token")
    scopes = data.get("scope")
    if not isinstance(scopes, list):
        scopes = []
    return {
        "access_token": token,
        "refresh_token": str(data.get("refresh_token") or "").strip() or None,
        "owner_id": str(data.get("owner_id") or "").strip() or None,
        "owner_name": str(data.get("owner_name") or "").strip() or None,
        "scopes": [str(item) for item in scopes],
        "access_expires_at": _unix_time(data.get("expires_at"), data.get("expires_in")),
        "refresh_expires_at": _unix_time(data.get("refresh_token_expires_at"), data.get("refresh_token_expires_in")),
    }
