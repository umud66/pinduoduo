from app.services.optimization_review import (
    canonical_validation_metrics,
    compare_review_snapshots,
    review_required_days,
)


def test_review_required_days_uses_sixty_percent_coverage() -> None:
    assert review_required_days(3) == 2
    assert review_required_days(7) == 5
    assert review_required_days(14) == 9


def test_validation_metric_names_are_normalized_without_duplicates() -> None:
    result = canonical_validation_metrics(["CTR", "点击率", "GMV 恢复幅度", "退款率", "推广 ROI"])
    assert result == ["ctr", "gmv", "refund_rate", "ad_roi"]


def test_review_marks_improvement_for_higher_better_metrics() -> None:
    baseline = {"gmv": 100, "ctr": 0.05}
    observed = {"gmv": 120, "ctr": 0.06}
    result = compare_review_snapshots(baseline, observed, ["GMV", "CTR"])
    assert result["outcome"] == "improved"
    assert result["effect_score"] == 0.2


def test_refund_rate_is_inverse_metric() -> None:
    baseline = {"refund_rate": 0.10}
    observed = {"refund_rate": 0.06}
    result = compare_review_snapshots(baseline, observed, ["退款率"])
    assert result["outcome"] == "improved"
    assert result["changes"]["refund_rate"]["effect"] == 0.4


def test_zero_baseline_does_not_invent_percentage_change() -> None:
    result = compare_review_snapshots({"gmv": 0}, {"gmv": 100}, ["GMV"])
    assert result["outcome"] == "insufficient_data"
    assert result["changes"]["gmv"]["change"] is None


def test_small_mixed_change_is_not_overclaimed() -> None:
    baseline = {"gmv": 100, "ctr": 0.05}
    observed = {"gmv": 104, "ctr": 0.049}
    result = compare_review_snapshots(baseline, observed, ["GMV", "CTR"])
    assert result["outcome"] == "stable_or_mixed"
    assert "不单独证明" in result["interpretation"]
