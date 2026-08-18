from __future__ import annotations

from typing import Any

CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "goods": ("goods", "product", "sku", "spu", "商品", "规格"),
    "orders": ("order", "trade", "transaction", "订单", "成交"),
    "refunds": ("refund", "after_sale", "aftersale", "售后", "退款"),
    "traffic": ("traffic", "visitor", "impression", "exposure", "click", "uv", "pv", "流量", "访客", "曝光", "点击"),
    "promotion": ("promotion", "ad", "advert", "roi", "spend", "推广", "投产"),
}


def _flatten_keys(value: Any, *, limit: int = 120) -> list[str]:
    keys: list[str] = []

    def walk(node: Any, depth: int) -> None:
        if len(keys) >= limit or depth > 3:
            return
        if isinstance(node, dict):
            for key, nested in node.items():
                keys.append(str(key).lower())
                walk(nested, depth + 1)
                if len(keys) >= limit:
                    break
        elif isinstance(node, list):
            for item in node[:3]:
                walk(item, depth + 1)

    walk(value, 0)
    return keys


def classify_response(url: str, payload: Any) -> tuple[str, list[str]]:
    haystack = url.lower() + " " + " ".join(_flatten_keys(payload))
    scores: dict[str, int] = {}
    evidence: dict[str, list[str]] = {}
    for category, hints in CATEGORY_HINTS.items():
        matched = [hint for hint in hints if hint.lower() in haystack]
        if matched:
            scores[category] = len(matched)
            evidence[category] = matched[:5]
    if not scores:
        return "unknown", []
    category = max(scores, key=lambda name: scores[name])
    return category, evidence[category]
