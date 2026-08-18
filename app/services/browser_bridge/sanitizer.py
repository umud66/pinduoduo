from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pwd",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
    "set-cookie",
    "session",
    "sessionid",
    "sid",
    "csrf",
    "csrf_token",
    "phone",
    "mobile",
    "tel",
    "receiver_phone",
    "receiver_mobile",
    "receiver_name",
    "consignee",
    "address",
    "receiver_address",
    "id_card",
    "identity_card",
}

MAX_CAPTURE_BYTES = 512 * 1024
PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    if lowered in SENSITIVE_KEYS:
        return True
    return any(token in lowered for token in (
        "password", "passwd", "access_token", "refresh_token", "authorization",
        "cookie", "receiver_", "consignee", "mobile", "phone", "address", "id_card",
    ))


@dataclass(slots=True)
class SanitizedPayload:
    value: Any
    redacted_fields: int


def safe_url(url: str) -> tuple[str, list[str]]:
    """Drop query values and fragments; retain query key names for endpoint discovery."""
    parsed = urlsplit(url)
    query_keys = sorted({key for key, _ in parse_qsl(parsed.query, keep_blank_values=True)})
    cleaned = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return cleaned, query_keys


def host_allowed(url: str, allowed_domains: list[str]) -> bool:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if not host:
        return False
    for raw_domain in allowed_domains:
        domain = raw_domain.lower().strip().lstrip(".").rstrip(".")
        if domain and (host == domain or host.endswith(f".{domain}")):
            return True
    return False


def is_capture_content_type(content_type: str | None) -> bool:
    value = (content_type or "").split(";", 1)[0].strip().lower()
    return value in {
        "application/json",
        "text/json",
        "application/problem+json",
        "application/graphql-response+json",
    } or value.endswith("+json")


def sanitize_json(value: Any) -> SanitizedPayload:
    redacted = 0

    def walk(node: Any) -> Any:
        nonlocal redacted
        if isinstance(node, dict):
            result: dict[str, Any] = {}
            for key, nested in node.items():
                key_text = str(key)
                if _sensitive_key(key_text):
                    result[key_text] = "[REDACTED]"
                    redacted += 1
                else:
                    result[key_text] = walk(nested)
            return result
        if isinstance(node, list):
            return [walk(item) for item in node[:500]]
        if isinstance(node, str):
            masked = PHONE_PATTERN.sub("[REDACTED_PHONE]", node)
            masked = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", masked)
            if masked != node:
                redacted += 1
            if len(masked) > 10_000:
                return masked[:10_000] + "…[TRUNCATED]"
            return masked
        return node

    return SanitizedPayload(walk(value), redacted)


def decode_and_sanitize(body: bytes, *, max_bytes: int = MAX_CAPTURE_BYTES) -> tuple[str | None, int, str | None]:
    if len(body) > max_bytes:
        return None, 0, f"response_too_large:{len(body)}"
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, 0, "invalid_json"
    cleaned = sanitize_json(decoded)
    return json.dumps(cleaned.value, ensure_ascii=False, separators=(",", ":")), cleaned.redacted_fields, None
