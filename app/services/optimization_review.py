from __future__ import annotations

from math import ceil
from typing import Any, Iterable

SUPPORTED_METRICS = {
    "gmv": {"label": "GMV", "inverse": False},
    "sales_qty": {"label": "销量", "inverse": False},
    "order_count": {"label": "订单数", "inverse": False},
    "ctr": {"label": "CTR", "inverse": False},
    "cvr": {"label": "CVR", "inverse": False},
    "refund_rate": {"label": "退款率", "inverse": True},
    "ad_roi": {"label": "推广 ROI", "inverse": False},
}


def review_required_days(window_days: int) -> int:
    return max(2, ceil(max(1, window_days) * 0.6))


def canonical_validation_metrics(labels: Iterable[str]) -> list[str]:
    result: list[str] = []
    for raw in labels:
        text = str(raw or "").strip().lower()
        candidates: list[str] = []
        if "ctr" in text or "点击率" in text:
            candidates.append("ctr")
        if "cvr" in text or "转化率" in text or "支付转化" in text:
            candidates.append("cvr")
        if "退款率" in text:
            candidates.append("refund_rate")
        if "roi" in text or "投产" in text:
            candidates.append("ad_roi")
        if "gmv" in text or "成交额" in text:
            candidates.append("gmv")
        if "销量" in text:
            candidates.append("sales_qty")
        if "订单" in text and "退款" not in text:
            candidates.append("order_count")
        for key in candidates:
            if key not in result:
                result.append(key)
    return result


def _change(observed: float | None, baseline: float | None) -> float | None:
    if observed is None or baseline is None or baseline <= 0:
        return None
    return (observed - baseline) / baseline


def compare_review_snapshots(
    baseline: dict[str, Any],
    observed: dict[str, Any],
    validation_metrics: Iterable[str],
) -> dict[str, Any]:
    keys = canonical_validation_metrics(validation_metrics)
    if not keys:
        keys = ["gmv"]

    changes: dict[str, Any] = {}
    effects: list[float] = []
    for key in SUPPORTED_METRICS:
        before = baseline.get(key)
        after = observed.get(key)
        change = _change(after, before)
        inverse = bool(SUPPORTED_METRICS[key]["inverse"])
        effect = -change if change is not None and inverse else change
        changes[key] = {
            "label": SUPPORTED_METRICS[key]["label"],
            "baseline": before,
            "observed": after,
            "change": change,
            "effect": round(effect, 4) if effect is not None else None,
            "inverse": inverse,
        }
        if key in keys and effect is not None:
            effects.append(effect)

    if not effects:
        outcome = "insufficient_data"
        effect_score = None
    else:
        effect_score = sum(effects) / len(effects)
        if effect_score >= 0.05:
            outcome = "improved"
        elif effect_score <= -0.05:
            outcome = "worsened"
        else:
            outcome = "stable_or_mixed"

    return {
        "outcome": outcome,
        "effect_score": round(effect_score, 4) if effect_score is not None else None,
        "monitored_metrics": keys,
        "available_metric_count": len(effects),
        "changes": changes,
        "interpretation": "复盘只表示执行前后指标的关联变化，不单独证明该动作造成了结果。",
    }
