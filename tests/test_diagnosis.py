from app.services.diagnosis.engine import MetricSnapshot, diagnose


def test_ctr_drop_is_detected_without_inventing_missing_metrics() -> None:
    current = MetricSnapshot(impression=1000, clicks=25, order_count=5, sales_qty=5, gmv=200, stock=100)
    baseline = MetricSnapshot(impression=1000, clicks=50, order_count=10, sales_qty=10, gmv=400, stock=100)
    result = diagnose(current, baseline)
    codes = {issue.code for issue in result.issues}
    assert "CTR_DROP" in codes
    assert "SALES_DROP" in codes
    assert result.health_score < 100


def test_missing_traffic_data_does_not_create_ctr_issue() -> None:
    current = MetricSnapshot(order_count=5, sales_qty=5, gmv=200, stock=100)
    baseline = MetricSnapshot(order_count=5, sales_qty=5, gmv=200, stock=100)
    result = diagnose(current, baseline)
    assert "CTR_DROP" not in {issue.code for issue in result.issues}
    assert result.data_quality["confidence"] in {"low", "medium"}


def test_full_funnel_decomposition_attributes_gmv_loss() -> None:
    current = MetricSnapshot(
        impression=700,
        clicks=35,
        order_count=7,
        sales_qty=7,
        gmv=280,
        price=40,
        stock=80,
    )
    baseline = MetricSnapshot(
        impression=1000,
        clicks=80,
        order_count=16,
        sales_qty=16,
        gmv=640,
        price=40,
        stock=100,
    )
    result = diagnose(current, baseline, baseline_days=7)
    assert result.decomposition["mode"] == "full_funnel"
    assert result.decomposition["estimated_gmv_loss"] == 360
    factors = result.decomposition["factors"]
    assert factors
    assert round(sum(float(item["estimated_loss"]) for item in factors), 2) == 360
    assert factors[0]["estimated_loss"] >= factors[-1]["estimated_loss"]


def test_issues_are_sorted_by_priority_and_include_validation_plan() -> None:
    current = MetricSnapshot(
        impression=1200,
        clicks=30,
        order_count=4,
        sales_qty=4,
        gmv=120,
        refund_count=2,
        stock=2,
        ad_cost=100,
        ad_gmv=50,
        price=30,
    )
    baseline = MetricSnapshot(
        impression=1400,
        clicks=84,
        order_count=14,
        sales_qty=14,
        gmv=560,
        refund_count=0,
        stock=90,
        ad_cost=60,
        ad_gmv=180,
        price=40,
    )
    result = diagnose(current, baseline, baseline_days=7)
    priorities = [issue.priority_score for issue in result.issues]
    assert priorities == sorted(priorities, reverse=True)
    assert all(0 <= issue.confidence <= 1 for issue in result.issues)
    assert all(issue.validation_metrics for issue in result.issues)
    assert result.summary


def test_low_stock_risk_is_high_priority() -> None:
    current = MetricSnapshot(order_count=20, sales_qty=20, gmv=800, stock=5)
    baseline = MetricSnapshot(order_count=18, sales_qty=18, gmv=720, stock=80)
    result = diagnose(current, baseline)
    issue = next(item for item in result.issues if item.code == "STOCK_RISK")
    assert issue.priority_score >= 70
    assert issue.evidence["sellable_days"] == 0.25
