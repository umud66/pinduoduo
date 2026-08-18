from datetime import date, timedelta

from app.services.trends import (
    MetricPoint,
    aggregate_points,
    build_30d_trend,
    build_issue_persistence,
    build_peer_comparison,
    build_window_comparison,
)


def point(day: date, *, gmv: float, sales: float = 10, orders: float = 8, impression=None, clicks=None):
    return MetricPoint(
        metric_date=day,
        gmv=gmv,
        sales_qty=sales,
        order_count=orders,
        impression=impression,
        clicks=clicks,
    )


def test_missing_traffic_stays_unknown_in_window_aggregate() -> None:
    start = date(2026, 8, 1)
    result = aggregate_points([point(start, gmv=100), point(start + timedelta(days=1), gmv=120)])
    assert result["ctr"] is None
    assert result["cvr"] is None
    assert result["traffic_days"] == 0


def test_week_over_week_detects_gmv_decline() -> None:
    latest = date(2026, 8, 14)
    points = []
    for offset in range(14):
        day = latest - timedelta(days=13 - offset)
        gmv = 200 if offset < 7 else 100
        points.append(point(day, gmv=gmv))
    result = build_window_comparison(points)
    assert result["week_over_week"]["gmv"]["change"] == -0.5
    assert result["trend_direction"] == "down"


def test_30d_trend_uses_points_without_inventing_missing_days() -> None:
    start = date(2026, 8, 1)
    points = [point(start + timedelta(days=i * 2), gmv=100 + i * 10) for i in range(8)]
    result = build_30d_trend(points)
    assert result["data_days"] == 8
    assert len(result["points"]) == 8


def test_peer_comparison_returns_rank_share_and_concentration() -> None:
    day = date(2026, 8, 18)
    peers = {
        1: [point(day, gmv=600, sales=30)],
        2: [point(day, gmv=300, sales=20)],
        3: [point(day, gmv=100, sales=10)],
    }
    result = build_peer_comparison(2, peers, names={1: "A", 2: "B", 3: "C"})
    assert result["target"]["rank"] == 2
    assert result["target"]["gmv_share"] == 0.3
    assert result["peer_count"] == 3
    assert result["gmv_concentration_hhi"] == 0.46


def test_issue_persistence_requires_calendar_continuity() -> None:
    latest = date(2026, 8, 18)
    history = [
        (latest, {"CTR_DROP", "SALES_DROP"}),
        (latest - timedelta(days=1), {"CTR_DROP"}),
        (latest - timedelta(days=2), {"CTR_DROP"}),
        (latest - timedelta(days=4), {"CTR_DROP"}),
    ]
    result = build_issue_persistence(["CTR_DROP", "SALES_DROP"], history)
    by_code = {item["code"]: item for item in result["issues"]}
    assert by_code["CTR_DROP"]["consecutive_days"] == 3
    assert by_code["SALES_DROP"]["consecutive_days"] == 1
    assert result["max_consecutive_days"] == 3
