from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class MetricPoint:
    metric_date: date
    sales_qty: float = 0.0
    order_count: float = 0.0
    gmv: float = 0.0
    refund_count: float = 0.0
    refund_amount: float = 0.0
    impression: float | None = None
    clicks: float | None = None
    visitors: float | None = None
    ad_cost: float | None = None
    ad_gmv: float | None = None
    price: float | None = None
    stock: float | None = None


def metric_point_from_row(row: Any) -> MetricPoint:
    def num(value: Any) -> float | None:
        return None if value is None else float(value)

    return MetricPoint(
        metric_date=row.metric_date,
        sales_qty=float(row.sales_qty or 0),
        order_count=float(row.order_count or 0),
        gmv=float(row.gmv or 0),
        refund_count=float(row.refund_count or 0),
        refund_amount=float(row.refund_amount or 0),
        impression=num(row.impression),
        clicks=num(row.clicks),
        visitors=num(row.visitors),
        ad_cost=num(row.ad_cost),
        ad_gmv=num(row.ad_gmv),
        price=num(row.price),
        stock=num(row.stock),
    )


def _change(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline is None or baseline <= 0:
        return None
    return (current - baseline) / baseline


def _average(values: Iterable[float | None]) -> float | None:
    items = [float(value) for value in values if value is not None]
    if not items:
        return None
    return float(mean(items))


def aggregate_points(points: Sequence[MetricPoint]) -> dict[str, Any]:
    items = sorted(points, key=lambda item: item.metric_date)
    days = len(items)
    sales_qty = sum(item.sales_qty for item in items)
    order_count = sum(item.order_count for item in items)
    gmv = sum(item.gmv for item in items)
    refund_count = sum(item.refund_count for item in items)
    refund_amount = sum(item.refund_amount for item in items)

    traffic_rows = [item for item in items if item.impression is not None and item.clicks is not None]
    traffic_impression = sum(float(item.impression or 0) for item in traffic_rows)
    traffic_clicks = sum(float(item.clicks or 0) for item in traffic_rows)
    ctr = traffic_clicks / traffic_impression if traffic_rows and traffic_impression > 0 else None

    click_rows = [item for item in items if item.clicks is not None]
    click_total = sum(float(item.clicks or 0) for item in click_rows)
    click_orders = sum(item.order_count for item in click_rows)
    cvr = click_orders / click_total if click_rows and click_total > 0 else None

    ad_rows = [item for item in items if item.ad_cost is not None and item.ad_gmv is not None]
    ad_cost = sum(float(item.ad_cost or 0) for item in ad_rows) if ad_rows else None
    ad_gmv = sum(float(item.ad_gmv or 0) for item in ad_rows) if ad_rows else None
    ad_roi = ad_gmv / ad_cost if ad_cost is not None and ad_gmv is not None and ad_cost > 0 else None

    return {
        "days": days,
        "sales_qty": round(sales_qty, 4),
        "order_count": round(order_count, 4),
        "gmv": round(gmv, 2),
        "refund_count": round(refund_count, 4),
        "refund_amount": round(refund_amount, 2),
        "avg_daily_sales_qty": round(sales_qty / days, 4) if days else None,
        "avg_daily_order_count": round(order_count / days, 4) if days else None,
        "avg_daily_gmv": round(gmv / days, 2) if days else None,
        "ctr": ctr,
        "cvr": cvr,
        "refund_rate": refund_count / order_count if order_count > 0 else None,
        "ad_roi": ad_roi,
        "avg_price": _average(item.price for item in items),
        "avg_stock": _average(item.stock for item in items),
        "traffic_days": len(traffic_rows),
        "click_days": len(click_rows),
        "ad_days": len(ad_rows),
    }


def _comparison_item(
    current: dict[str, Any],
    baseline: dict[str, Any],
    *,
    field: str,
    current_field: str | None = None,
    baseline_field: str | None = None,
) -> dict[str, Any]:
    c_field = current_field or field
    b_field = baseline_field or field
    current_value = current.get(c_field)
    baseline_value = baseline.get(b_field)
    return {
        "current": current_value,
        "baseline": baseline_value,
        "change": _change(current_value, baseline_value),
    }


def _direction(change: float | None, *, tolerance: float = 0.08) -> str:
    if change is None:
        return "unknown"
    if change <= -tolerance:
        return "down"
    if change >= tolerance:
        return "up"
    return "flat"


def build_window_comparison(points: Sequence[MetricPoint]) -> dict[str, Any]:
    if not points:
        return {
            "latest_date": None,
            "today_vs_7d": {},
            "week_over_week": {},
            "trend_direction": "unknown",
            "data_days": 0,
        }

    ordered = sorted(points, key=lambda item: item.metric_date)
    latest = ordered[-1].metric_date
    by_date = {item.metric_date: item for item in ordered}

    current_point = by_date.get(latest)
    previous_7 = [
        by_date[d]
        for d in (latest - timedelta(days=offset) for offset in range(1, 8))
        if d in by_date
    ]
    recent_7 = [
        by_date[d]
        for d in (latest - timedelta(days=offset) for offset in range(0, 7))
        if d in by_date
    ]
    prior_7 = [
        by_date[d]
        for d in (latest - timedelta(days=offset) for offset in range(7, 14))
        if d in by_date
    ]

    current = aggregate_points([current_point] if current_point else [])
    prev = aggregate_points(previous_7)
    recent = aggregate_points(recent_7)
    prior = aggregate_points(prior_7)

    today_vs_7d = {
        "gmv": _comparison_item(current, prev, field="gmv", baseline_field="avg_daily_gmv"),
        "sales_qty": _comparison_item(current, prev, field="sales_qty", baseline_field="avg_daily_sales_qty"),
        "order_count": _comparison_item(current, prev, field="order_count", baseline_field="avg_daily_order_count"),
        "ctr": _comparison_item(current, prev, field="ctr"),
        "cvr": _comparison_item(current, prev, field="cvr"),
        "refund_rate": _comparison_item(current, prev, field="refund_rate"),
        "ad_roi": _comparison_item(current, prev, field="ad_roi"),
    }
    week_over_week = {
        "gmv": _comparison_item(recent, prior, field="avg_daily_gmv"),
        "sales_qty": _comparison_item(recent, prior, field="avg_daily_sales_qty"),
        "order_count": _comparison_item(recent, prior, field="avg_daily_order_count"),
        "ctr": _comparison_item(recent, prior, field="ctr"),
        "cvr": _comparison_item(recent, prior, field="cvr"),
        "refund_rate": _comparison_item(recent, prior, field="refund_rate"),
        "ad_roi": _comparison_item(recent, prior, field="ad_roi"),
    }

    gmv_change = week_over_week["gmv"]["change"]
    return {
        "latest_date": latest.isoformat(),
        "today_vs_7d": today_vs_7d,
        "week_over_week": week_over_week,
        "trend_direction": _direction(gmv_change),
        "data_days": len(ordered),
        "window_coverage": {
            "previous_7_days": len(previous_7),
            "recent_7_days": len(recent_7),
            "prior_7_days": len(prior_7),
        },
    }


def build_30d_trend(points: Sequence[MetricPoint]) -> dict[str, Any]:
    ordered = sorted(points, key=lambda item: item.metric_date)[-30:]
    if not ordered:
        return {"points": [], "direction": "unknown", "change": None, "data_days": 0}

    points_payload = [
        {
            "date": item.metric_date.isoformat(),
            "gmv": round(item.gmv, 2),
            "sales_qty": round(item.sales_qty, 4),
            "order_count": round(item.order_count, 4),
            "refund_rate": item.refund_count / item.order_count if item.order_count > 0 else None,
            "ctr": item.clicks / item.impression
            if item.impression is not None and item.clicks is not None and item.impression > 0
            else None,
            "cvr": item.order_count / item.clicks if item.clicks is not None and item.clicks > 0 else None,
            "ad_roi": item.ad_gmv / item.ad_cost
            if item.ad_cost is not None and item.ad_gmv is not None and item.ad_cost > 0
            else None,
        }
        for item in ordered
    ]

    recent = aggregate_points(ordered[-7:])
    if len(ordered) >= 14:
        early = aggregate_points(ordered[:7])
        change = _change(recent.get("avg_daily_gmv"), early.get("avg_daily_gmv"))
    else:
        change = None

    return {
        "points": points_payload,
        "direction": _direction(change),
        "change": change,
        "data_days": len(ordered),
        "recent_7": recent,
    }


def build_peer_comparison(
    target_sku_id: int,
    peers: Mapping[int, Sequence[MetricPoint]],
    *,
    names: Mapping[int, str] | None = None,
) -> dict[str, Any]:
    names = names or {}
    rows: list[dict[str, Any]] = []
    for sku_id, points in peers.items():
        aggregate = aggregate_points(points)
        rows.append(
            {
                "sku_id": sku_id,
                "sku_name": names.get(sku_id, str(sku_id)),
                "gmv": float(aggregate.get("gmv") or 0),
                "sales_qty": float(aggregate.get("sales_qty") or 0),
                "order_count": float(aggregate.get("order_count") or 0),
                "days": int(aggregate.get("days") or 0),
            }
        )

    rows.sort(key=lambda item: (item["gmv"], item["sales_qty"]), reverse=True)
    total_gmv = sum(float(item["gmv"]) for item in rows)
    total_sales = sum(float(item["sales_qty"]) for item in rows)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
        row["gmv_share"] = row["gmv"] / total_gmv if total_gmv > 0 else None
        row["sales_share"] = row["sales_qty"] / total_sales if total_sales > 0 else None
        row["is_target"] = row["sku_id"] == target_sku_id

    target = next((item for item in rows if item["sku_id"] == target_sku_id), None)
    others = [item for item in rows if item["sku_id"] != target_sku_id]
    peer_avg_gmv = mean(float(item["gmv"]) for item in others) if others else None
    relative = _change(float(target["gmv"]), peer_avg_gmv) if target and peer_avg_gmv is not None else None
    shares = [float(item["gmv_share"] or 0) for item in rows]
    hhi = sum(share * share for share in shares) if shares else None

    if hhi is None:
        concentration = "unknown"
    elif hhi >= 0.60:
        concentration = "high"
    elif hhi >= 0.35:
        concentration = "medium"
    else:
        concentration = "balanced"

    return {
        "target": target,
        "peers": rows,
        "peer_count": len(rows),
        "peer_avg_gmv": round(peer_avg_gmv, 2) if peer_avg_gmv is not None else None,
        "relative_to_peer_avg": relative,
        "gmv_concentration_hhi": round(hhi, 4) if hhi is not None else None,
        "concentration": concentration,
    }


def build_issue_persistence(
    current_codes: Sequence[str],
    history: Sequence[tuple[date, set[str]]],
) -> dict[str, Any]:
    if not current_codes or not history:
        return {"issues": [], "max_consecutive_days": 0, "history_records": len(history)}

    ordered = sorted(history, key=lambda item: item[0], reverse=True)
    latest_date = ordered[0][0]
    issues = []
    for code in current_codes:
        expected = latest_date
        consecutive = 0
        first_date: date | None = None
        for period_end, codes in ordered:
            if period_end != expected:
                break
            if code not in codes:
                break
            consecutive += 1
            first_date = period_end
            expected = period_end - timedelta(days=1)
        issues.append(
            {
                "code": code,
                "consecutive_days": consecutive,
                "since": first_date.isoformat() if first_date else None,
            }
        )

    return {
        "issues": issues,
        "max_consecutive_days": max((item["consecutive_days"] for item in issues), default=0),
        "history_records": len(history),
    }
