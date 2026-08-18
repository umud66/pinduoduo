from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Any, Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DiagnosisResult, Product, Sku, SkuDailyMetric
from app.services.trends import (
    MetricPoint,
    aggregate_points,
    build_issue_persistence,
    build_window_comparison,
    metric_point_from_row,
)


@dataclass(frozen=True, slots=True)
class StructureWindow:
    prior: Mapping[int, Sequence[MetricPoint]]
    recent: Mapping[int, Sequence[MetricPoint]]


def _change(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None or baseline <= 0:
        return None
    return (current - baseline) / baseline


def _safe_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _mean(values: Sequence[float]) -> float | None:
    return float(mean(values)) if values else None


def build_change_points(
    points: Sequence[MetricPoint],
    *,
    field: str = "gmv",
    segment_days: int = 3,
    minimum_change: float = 0.20,
    max_candidates: int = 3,
) -> dict[str, Any]:
    """Detect simple explainable level shifts using adjacent real-data windows.

    This is deliberately deterministic and dependency-free. It does not invent
    missing calendar days; confidence is reduced when the split spans a large gap.
    """

    ordered = sorted(points, key=lambda item: item.metric_date)[-30:]
    if len(ordered) < segment_days * 2:
        return {
            "field": field,
            "detected": False,
            "primary": None,
            "candidates": [],
            "data_days": len(ordered),
            "minimum_change": minimum_change,
        }

    candidates: list[dict[str, Any]] = []
    for split in range(segment_days, len(ordered) - segment_days + 1):
        before_points = ordered[split - segment_days : split]
        after_points = ordered[split : split + segment_days]
        before_values = [float(getattr(item, field)) for item in before_points]
        after_values = [float(getattr(item, field)) for item in after_points]
        before = _mean(before_values)
        after = _mean(after_values)
        change = _change(after, before)
        if change is None or abs(change) < minimum_change:
            continue

        gap_days = max(1, (after_points[0].metric_date - before_points[-1].metric_date).days)
        gap_factor = 1.0 if gap_days <= 2 else max(0.45, 1.0 - (gap_days - 2) * 0.12)
        magnitude_factor = min(1.0, abs(change) / 0.60)
        confidence = round(min(0.96, (0.62 + 0.28 * magnitude_factor) * gap_factor), 2)
        split_date = after_points[0].metric_date
        latest_date = ordered[-1].metric_date
        candidates.append(
            {
                "date": split_date.isoformat(),
                "direction": "down" if change < 0 else "up",
                "change": round(change, 4),
                "before_avg": round(before or 0.0, 2),
                "after_avg": round(after or 0.0, 2),
                "confidence": confidence,
                "calendar_gap_days": gap_days,
                "recent": (latest_date - split_date).days <= 7,
                "segment_days": segment_days,
            }
        )

    candidates.sort(key=lambda item: (abs(float(item["change"])), float(item["confidence"])), reverse=True)
    selected: list[dict[str, Any]] = []
    for item in candidates:
        item_date = date.fromisoformat(str(item["date"]))
        if any(abs((item_date - date.fromisoformat(str(existing["date"]))).days) <= 2 for existing in selected):
            continue
        selected.append(item)
        if len(selected) >= max_candidates:
            break
    selected.sort(key=lambda item: item["date"], reverse=True)
    primary = max(selected, key=lambda item: abs(float(item["change"])), default=None)
    return {
        "field": field,
        "detected": bool(selected),
        "primary": primary,
        "candidates": selected,
        "data_days": len(ordered),
        "minimum_change": minimum_change,
    }


def build_structure_shift(
    target_sku_id: int,
    windows: StructureWindow,
    *,
    names: Mapping[int, str] | None = None,
) -> dict[str, Any]:
    """Describe SKU share migration and conservative cannibalization candidates."""

    names = names or {}
    sku_ids = sorted(set(windows.prior) | set(windows.recent))
    rows: list[dict[str, Any]] = []
    total_prior = 0.0
    total_recent = 0.0
    for sku_id in sku_ids:
        prior = aggregate_points(windows.prior.get(sku_id, []))
        recent = aggregate_points(windows.recent.get(sku_id, []))
        prior_gmv = float(prior.get("gmv") or 0)
        recent_gmv = float(recent.get("gmv") or 0)
        total_prior += prior_gmv
        total_recent += recent_gmv
        rows.append(
            {
                "sku_id": sku_id,
                "sku_name": names.get(sku_id, str(sku_id)),
                "prior_gmv": round(prior_gmv, 2),
                "recent_gmv": round(recent_gmv, 2),
                "gmv_change": _change(recent_gmv, prior_gmv),
                "prior_days": int(prior.get("days") or 0),
                "recent_days": int(recent.get("days") or 0),
            }
        )

    for row in rows:
        row["prior_share"] = row["prior_gmv"] / total_prior if total_prior > 0 else None
        row["recent_share"] = row["recent_gmv"] / total_recent if total_recent > 0 else None
        if row["prior_share"] is not None and row["recent_share"] is not None:
            row["share_change"] = row["recent_share"] - row["prior_share"]
        else:
            row["share_change"] = None

    prior_hhi = sum(float(row["prior_share"] or 0) ** 2 for row in rows) if total_prior > 0 else None
    recent_hhi = sum(float(row["recent_share"] or 0) ** 2 for row in rows) if total_recent > 0 else None
    product_change = _change(total_recent, total_prior)

    pairs: list[dict[str, Any]] = []
    losers = [row for row in rows if row["gmv_change"] is not None and row["gmv_change"] <= -0.20]
    winners = [row for row in rows if row["gmv_change"] is not None and row["gmv_change"] >= 0.20]
    product_stable = product_change is not None and -0.15 <= product_change <= 0.15
    if product_stable:
        for loser in losers:
            loss = max(0.0, float(loser["prior_gmv"]) - float(loser["recent_gmv"]))
            if loss <= 0:
                continue
            for winner in winners:
                if winner["sku_id"] == loser["sku_id"]:
                    continue
                gain = max(0.0, float(winner["recent_gmv"]) - float(winner["prior_gmv"]))
                transfer = min(loss, gain)
                transfer_ratio = transfer / loss if loss > 0 else 0.0
                coverage = min(
                    int(loser["prior_days"]), int(loser["recent_days"]),
                    int(winner["prior_days"]), int(winner["recent_days"]),
                )
                if transfer_ratio < 0.35 or coverage < 3:
                    continue
                confidence = round(min(0.95, 0.55 + min(coverage, 7) / 7 * 0.20 + min(transfer_ratio, 1.0) * 0.20), 2)
                pairs.append(
                    {
                        "loser_sku_id": loser["sku_id"],
                        "loser_name": loser["sku_name"],
                        "winner_sku_id": winner["sku_id"],
                        "winner_name": winner["sku_name"],
                        "estimated_transfer": round(transfer, 2),
                        "transfer_ratio": round(transfer_ratio, 4),
                        "confidence": confidence,
                    }
                )
    pairs.sort(key=lambda item: (item["estimated_transfer"], item["confidence"]), reverse=True)

    target_pair = next(
        (pair for pair in pairs if pair["loser_sku_id"] == target_sku_id or pair["winner_sku_id"] == target_sku_id),
        None,
    )
    if target_pair and target_pair["loser_sku_id"] == target_sku_id:
        role = "loser"
    elif target_pair and target_pair["winner_sku_id"] == target_sku_id:
        role = "winner"
    else:
        role = "neutral"

    target = next((row for row in rows if row["sku_id"] == target_sku_id), None)
    return {
        "target": target,
        "rows": rows,
        "product_prior_gmv": round(total_prior, 2),
        "product_recent_gmv": round(total_recent, 2),
        "product_gmv_change": product_change,
        "prior_hhi": round(prior_hhi, 4) if prior_hhi is not None else None,
        "recent_hhi": round(recent_hhi, 4) if recent_hhi is not None else None,
        "hhi_change": round(recent_hhi - prior_hhi, 4) if prior_hhi is not None and recent_hhi is not None else None,
        "cannibalization_candidate": bool(target_pair),
        "role": role,
        "primary_pair": target_pair,
        "pairs": pairs[:5],
        "peer_count": len(rows),
        "product_stable_for_detection": product_stable,
    }


def build_action_priority(
    base_priority: int | None,
    *,
    window_comparison: Mapping[str, Any],
    persistence: Mapping[str, Any],
    change_points: Mapping[str, Any],
    structure_shift: Mapping[str, Any],
) -> dict[str, Any]:
    """Add explainable urgency context without mutating diagnosis priority_score."""

    if base_priority is None:
        return {
            "available": False,
            "base_priority": None,
            "action_priority": None,
            "boost": 0,
            "band": "unavailable",
            "adjustments": [],
        }

    adjustments: list[dict[str, Any]] = []
    week_change = (((window_comparison.get("week_over_week") or {}).get("gmv") or {}).get("change"))
    if week_change is not None:
        if week_change <= -0.35:
            adjustments.append({"code": "TREND_7D", "points": 12, "reason": "近 7 日日均 GMV 较前 7 日下降至少 35%"})
        elif week_change <= -0.20:
            adjustments.append({"code": "TREND_7D", "points": 8, "reason": "近 7 日日均 GMV 较前 7 日下降至少 20%"})
        elif week_change <= -0.08:
            adjustments.append({"code": "TREND_7D", "points": 4, "reason": "近 7 日日均 GMV 呈明确下滑趋势"})

    days = int(persistence.get("max_consecutive_days") or 0)
    if days >= 7:
        adjustments.append({"code": "PERSISTENCE", "points": 10, "reason": f"当前问题最长连续 {days} 天"})
    elif days >= 3:
        adjustments.append({"code": "PERSISTENCE", "points": 6, "reason": f"当前问题最长连续 {days} 天"})
    elif days >= 2:
        adjustments.append({"code": "PERSISTENCE", "points": 3, "reason": f"当前问题已连续 {days} 天"})

    primary = change_points.get("primary") or {}
    if primary.get("recent") and primary.get("direction") == "down":
        magnitude = abs(float(primary.get("change") or 0))
        points = 8 if magnitude >= 0.40 else 5
        adjustments.append({"code": "CHANGE_POINT", "points": points, "reason": f"最近出现 {magnitude * 100:.0f}% 的下降变化点"})

    if structure_shift.get("cannibalization_candidate") and structure_shift.get("role") == "loser":
        pair = structure_shift.get("primary_pair") or {}
        adjustments.append({
            "code": "SKU_SHIFT",
            "points": 6,
            "reason": f"同商品销量结构可能向 {pair.get('winner_name', '其他 SKU')} 转移",
        })

    raw_boost = sum(int(item["points"]) for item in adjustments)
    boost = min(25, raw_boost)
    action_priority = min(100, int(base_priority) + boost)
    if action_priority >= 85:
        band = "urgent"
    elif action_priority >= 70:
        band = "high"
    elif action_priority >= 50:
        band = "medium"
    else:
        band = "normal"
    return {
        "available": True,
        "base_priority": int(base_priority),
        "action_priority": action_priority,
        "boost": boost,
        "band": band,
        "adjustments": adjustments,
        "note": "action_priority 只用于当前运营排队，不回写或替换 diagnosis.priority_score",
    }


def _diagnosis_history(rows: Sequence[DiagnosisResult]) -> list[tuple[date, set[str]]]:
    by_date: dict[date, set[str]] = {}
    for row in rows:
        payload = _safe_json(row.diagnosis_json)
        codes = {
            str(issue.get("code"))
            for issue in payload.get("issues", [])
            if isinstance(issue, dict) and issue.get("code")
        }
        by_date.setdefault(row.period_end, set()).update(codes)
    return sorted(by_date.items(), key=lambda item: item[0], reverse=True)


def _base_priority(diagnosis: DiagnosisResult | None) -> tuple[int | None, list[str]]:
    payload = _safe_json(diagnosis.diagnosis_json if diagnosis else None)
    issues = [item for item in payload.get("issues", []) if isinstance(item, dict)]
    priorities = [int(item.get("priority_score")) for item in issues if item.get("priority_score") is not None]
    codes = [str(item.get("code")) for item in issues if item.get("code")]
    return (max(priorities) if priorities else None, codes)


def sku_decision_support(session: Session, sku_id: int) -> dict[str, Any]:
    sku = session.get(Sku, sku_id)
    if sku is None:
        raise LookupError("SKU 不存在")
    product = session.get(Product, sku.product_id)
    if product is None:
        raise LookupError("商品不存在")

    metric_rows = session.scalars(
        select(SkuDailyMetric)
        .where(SkuDailyMetric.sku_id == sku_id)
        .order_by(SkuDailyMetric.metric_date.desc())
        .limit(30)
    ).all()
    points = [metric_point_from_row(row) for row in reversed(metric_rows)]
    latest_date = max((point.metric_date for point in points), default=None)
    window = build_window_comparison(points)
    change_points = build_change_points(points)

    peer_skus = session.scalars(select(Sku).where(Sku.product_id == product.id).order_by(Sku.id)).all()
    peer_ids = [item.id for item in peer_skus]
    names = {item.id: item.sku_name or item.platform_sku_id for item in peer_skus}
    prior_map: dict[int, list[MetricPoint]] = {peer_id: [] for peer_id in peer_ids}
    recent_map: dict[int, list[MetricPoint]] = {peer_id: [] for peer_id in peer_ids}
    if latest_date is not None and peer_ids:
        rows = session.scalars(
            select(SkuDailyMetric)
            .where(
                SkuDailyMetric.sku_id.in_(peer_ids),
                SkuDailyMetric.metric_date >= latest_date - timedelta(days=13),
                SkuDailyMetric.metric_date <= latest_date,
            )
            .order_by(SkuDailyMetric.metric_date)
        ).all()
        recent_start = latest_date - timedelta(days=6)
        for row in rows:
            point = metric_point_from_row(row)
            if row.metric_date >= recent_start:
                recent_map[row.sku_id].append(point)
            else:
                prior_map[row.sku_id].append(point)
    structure = build_structure_shift(
        sku_id,
        StructureWindow(prior=prior_map, recent=recent_map),
        names=names,
    )

    diagnoses = session.scalars(
        select(DiagnosisResult)
        .where(DiagnosisResult.sku_id == sku_id)
        .order_by(DiagnosisResult.period_end.desc(), DiagnosisResult.id.desc())
        .limit(30)
    ).all()
    current_diagnosis = diagnoses[0] if diagnoses else None
    base_priority, current_codes = _base_priority(current_diagnosis)
    persistence = build_issue_persistence(current_codes, _diagnosis_history(diagnoses))
    action_priority = build_action_priority(
        base_priority,
        window_comparison=window,
        persistence=persistence,
        change_points=change_points,
        structure_shift=structure,
    )

    summary: list[str] = []
    if action_priority.get("available") and action_priority.get("boost"):
        summary.append(
            f"运营处理优先级由 {action_priority['base_priority']} 提升到 {action_priority['action_priority']}，"
            f"共增加 {action_priority['boost']} 分趋势上下文"
        )
    primary = change_points.get("primary") or {}
    if primary:
        summary.append(
            f"{primary.get('date')} 附近出现 GMV {'下降' if primary.get('direction') == 'down' else '上升'}变化点 "
            f"{abs(float(primary.get('change') or 0)) * 100:.1f}%"
        )
    pair = structure.get("primary_pair") or {}
    if structure.get("role") == "loser":
        summary.append(f"同商品 GMV 结构可能向 {pair.get('winner_name', '其他 SKU')} 转移")
    elif structure.get("role") == "winner":
        summary.append(f"当前 SKU 可能承接了来自 {pair.get('loser_name', '其他 SKU')} 的商品内份额")

    return {
        "sku_id": sku.id,
        "product_id": product.id,
        "latest_date": latest_date.isoformat() if latest_date else None,
        "change_points": change_points,
        "structure_shift": structure,
        "action_priority": action_priority,
        "summary": summary,
        "data_quality": {
            "metric_days": len(points),
            "peer_count": len(peer_ids),
            "has_two_full_weeks": (
                window.get("window_coverage", {}).get("recent_7_days") == 7
                and window.get("window_coverage", {}).get("prior_7_days") == 7
            ),
            "diagnosis_history_records": len(diagnoses),
        },
    }
