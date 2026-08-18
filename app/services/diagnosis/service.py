from __future__ import annotations

import json

from sqlalchemy import select

from app.db.database import session_scope
from app.db.models import DiagnosisResult, SkuDailyMetric
from app.services.diagnosis.engine import MetricSnapshot, average_snapshots, diagnose, number


def metric_to_snapshot(metric: SkuDailyMetric) -> MetricSnapshot:
    return MetricSnapshot(
        sales_qty=float(metric.sales_qty or 0),
        order_count=float(metric.order_count or 0),
        gmv=float(metric.gmv or 0),
        refund_count=float(metric.refund_count or 0),
        refund_amount=float(metric.refund_amount or 0),
        impression=number(metric.impression),
        clicks=number(metric.clicks),
        visitors=number(metric.visitors),
        stock=number(metric.stock),
        ad_cost=number(metric.ad_cost),
        ad_gmv=number(metric.ad_gmv),
    )


def diagnose_latest_sku(sku_id: int) -> dict[str, object]:
    with session_scope() as session:
        metrics = session.scalars(
            select(SkuDailyMetric)
            .where(SkuDailyMetric.sku_id == sku_id)
            .order_by(SkuDailyMetric.metric_date.desc())
            .limit(8)
        ).all()
        if not metrics:
            raise LookupError("该 SKU 暂无每日指标数据")

        current_metric = metrics[0]
        current = metric_to_snapshot(current_metric)
        baseline = average_snapshots(metric_to_snapshot(m) for m in metrics[1:])
        result = diagnose(current, baseline)
        payload = result.as_dict()
        payload["sku_id"] = sku_id
        payload["period_end"] = current_metric.metric_date.isoformat()
        payload["baseline_days"] = len(metrics[1:])

        stored = DiagnosisResult(
            sku_id=sku_id,
            period_end=current_metric.metric_date,
            health_score=result.health_score,
            severity=result.severity,
            diagnosis_json=json.dumps(payload, ensure_ascii=False),
        )
        session.add(stored)
        session.flush()
        payload["diagnosis_id"] = stored.id
        return payload


def build_ai_context(diagnosis_payload: dict[str, object]) -> str:
    return (
        "你是电商运营诊断助手。下面的数据已经由程序完成计算，请不要修改指标或虚构缺失数据。"
        "只根据给定问题提出按优先级排序、可执行、可验证的优化动作；缺少曝光/点击等数据时要明确说明。\n\n"
        + json.dumps(diagnosis_payload, ensure_ascii=False, indent=2)
    )
