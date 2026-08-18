from app.services.diagnosis.engine import MetricSnapshot, diagnose


def test_ctr_drop_is_detected_without_inventing_missing_metrics() -> None:
    current = MetricSnapshot(impression=1000, clicks=25, order_count=5, sales_qty=5, stock=100)
    baseline = MetricSnapshot(impression=1000, clicks=50, order_count=10, sales_qty=10, stock=100)
    result = diagnose(current, baseline)
    codes = {issue.code for issue in result.issues}
    assert "CTR_DROP" in codes
    assert "SALES_DROP" in codes
    assert result.health_score < 100


def test_missing_traffic_data_does_not_create_ctr_issue() -> None:
    current = MetricSnapshot(order_count=5, sales_qty=5, stock=100)
    baseline = MetricSnapshot(order_count=5, sales_qty=5, stock=100)
    result = diagnose(current, baseline)
    assert "CTR_DROP" not in {issue.code for issue in result.issues}
