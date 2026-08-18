import json

from app.services.browser_bridge.classifier import classify_response
from app.services.browser_bridge.sanitizer import (
    decode_and_sanitize,
    host_allowed,
    safe_url,
    sanitize_json,
)


def test_safe_url_drops_query_values_but_keeps_keys():
    url, keys = safe_url("https://mms.example.com/api?a=1&token=secret&b=2#frag")
    assert url == "https://mms.example.com/api"
    assert keys == ["a", "b", "token"]
    assert "secret" not in url


def test_domain_allowlist_supports_subdomains_only():
    assert host_allowed("https://mms.pinduoduo.com/api", ["pinduoduo.com"])
    assert host_allowed("https://pinduoduo.com/api", ["pinduoduo.com"])
    assert not host_allowed("https://pinduoduo.com.attacker.example/api", ["pinduoduo.com"])


def test_sanitizer_redacts_auth_and_buyer_pii_recursively():
    cleaned = sanitize_json({
        "access_token": "abc",
        "data": {"mobile": "13800000000", "gmv": 100, "receiver_address": "x"},
    })
    assert cleaned.redacted_fields == 3
    assert cleaned.value["access_token"] == "[REDACTED]"
    assert cleaned.value["data"]["mobile"] == "[REDACTED]"
    assert cleaned.value["data"]["gmv"] == 100


def test_decode_rejects_large_body():
    body = json.dumps({"data": "x" * 100}).encode()
    text, redacted, error = decode_and_sanitize(body, max_bytes=32)
    assert text is None
    assert redacted == 0
    assert error and error.startswith("response_too_large")


def test_classifier_finds_orders_from_url_and_keys():
    category, evidence = classify_response("https://x.example/api/order/list", {"order_list": [{"order_sn": "1"}]})
    assert category == "orders"
    assert evidence


def test_classifier_keeps_unrecognized_response_unknown():
    category, evidence = classify_response("https://x.example/api/config", {"locale": "zh-CN"})
    assert category == "unknown"
    assert evidence == []
