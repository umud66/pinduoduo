from datetime import date, timedelta

from app.services.decision_support import (
    StructureWindow,
    build_action_priority,
    build_change_points,
    build_structure_shift,
)
from app.services.trends import MetricPoint


def point(day: date, gmv: float) -> MetricPoint:
    return MetricPoint(metric_date=day, gmv=gmv, sales_qty=gmv / 10, order_count=gmv / 20)


def test_change_point_detects_recent_level_drop() -> None:
    start = date(2026, 8, 1)
    points = [point(start + timedelta(days=i), 200 if i < 10 else 90) for i in range(16)]
    result = build_change_points(points)
    assert result["detected"] is True
    assert result["primary"]["direction"] == "down"
    assert result["primary"]["change"] <= -0.5
    assert result["primary"]["recent"] is True


def test_change_point_requires_enough_data() -> None:
    start = date(2026, 8, 1)
    result = build_change_points([point(start + timedelta(days=i), 100) for i in range(5)])
    assert result["detected"] is False
    assert result["primary"] is None


def test_structure_shift_detects_candidate_when_product_total_is_stable() -> None:
    end = date(2026, 8, 18)
    prior_days = [end - timedelta(days=i) for i in range(13, 6, -1)]
    recent_days = [end - timedelta(days=i) for i in range(6, -1, -1)]
    windows = StructureWindow(
        prior={
            1: [point(day, 200) for day in prior_days],
            2: [point(day, 100) for day in prior_days],
        },
        recent={
            1: [point(day, 100) for day in recent_days],
            2: [point(day, 200) for day in recent_days],
        },
    )
    result = build_structure_shift(1, windows, names={1: "规格 A", 2: "规格 B"})
    assert result["product_gmv_change"] == 0
    assert result["cannibalization_candidate"] is True
    assert result["role"] == "loser"
    assert result["primary_pair"]["winner_sku_id"] == 2
    assert result["primary_pair"]["transfer_ratio"] == 1.0


def test_structure_shift_does_not_call_market_drop_cannibalization() -> None:
    end = date(2026, 8, 18)
    prior = [end - timedelta(days=i) for i in range(13, 6, -1)]
    recent = [end - timedelta(days=i) for i in range(6, -1, -1)]
    windows = StructureWindow(
        prior={1: [point(day, 200) for day in prior], 2: [point(day, 200) for day in prior]},
        recent={1: [point(day, 80) for day in recent], 2: [point(day, 100) for day in recent]},
    )
    result = build_structure_shift(1, windows)
    assert result["product_gmv_change"] < -0.5
    assert result["cannibalization_candidate"] is False


def test_action_priority_is_explainable_and_capped() -> None:
    result = build_action_priority(
        78,
        window_comparison={"week_over_week": {"gmv": {"change": -0.5}}},
        persistence={"max_consecutive_days": 8},
        change_points={"primary": {"recent": True, "direction": "down", "change": -0.5}},
        structure_shift={
            "cannibalization_candidate": True,
            "role": "loser",
            "primary_pair": {"winner_name": "规格 B"},
        },
    )
    assert result["base_priority"] == 78
    assert result["boost"] == 25
    assert result["action_priority"] == 100
    assert {item["code"] for item in result["adjustments"]} == {
        "TREND_7D",
        "PERSISTENCE",
        "CHANGE_POINT",
        "SKU_SHIFT",
    }


def test_action_priority_unavailable_without_diagnosis_priority() -> None:
    result = build_action_priority(
        None,
        window_comparison={},
        persistence={},
        change_points={},
        structure_shift={},
    )
    assert result["available"] is False
    assert result["action_priority"] is None
