from __future__ import annotations

import json

from sqlalchemy import select

from app.db.database import session_scope
from app.db.models import DiagnosisResult, SkuDailyMetric
from app.services.diagnosis.engine import (
    MetricSnapshot,
    average_snapshots,
    diagnose,
    number,
    snapshot_payload,
)


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
        ad_clicks=number(metric.ad_clicks),
        ad_orders=number(metric.ad_orders),
        ad_gmv=number(metric.ad_gmv),
        price=number(metric.price),
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
        baseline_items = [metric_to_snapshot(m) for m in metrics[1:]]
        current = metric_to_snapshot(current_metric)
        baseline = average_snapshots(baseline_items)
        baseline_days = len(baseline_items)
        result = diagnose(current, baseline, baseline_days=baseline_days)

        payload = result.as_dict()
        payload["sku_id"] = sku_id
        payload["period_end"] = current_metric.metric_date.isoformat()
        payload["baseline_days"] = baseline_days
        payload["current"] = snapshot_payload(current)
        payload["baseline"] = snapshot_payload(baseline)
        diagnosis_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        stored = session.scalar(
            select(DiagnosisResult)
            .where(
                DiagnosisResult.sku_id == sku_id,
                DiagnosisResult.period_end == current_metric.metric_date,
            )
            .order_by(DiagnosisResult.id.desc())
            .limit(1)
        )
        if stored is None:
            stored = DiagnosisResult(
                sku_id=sku_id,
                period_end=current_metric.metric_date,
                health_score=result.health_score,
                severity=result.severity,
                diagnosis_json=diagnosis_json,
            )
            session.add(stored)
        else:
            changed = stored.diagnosis_json != diagnosis_json
            stored.health_score = result.health_score
            stored.severity = result.severity
            stored.diagnosis_json = diagnosis_json
            if changed:
                stored.ai_analysis_json = None
        session.flush()
        payload["diagnosis_id"] = stored.id
        return payload


def diagnose_shop_skus(shop_id: int, *, limit: int = 2000) -> dict[str, object]:
    with session_scope() as session:
        sku_ids = session.scalars(
            select(SkuDailyMetric.sku_id)
            .where(SkuDailyMetric.shop_id == shop_id)
            .distinct()
            .order_by(SkuDailyMetric.sku_id)
            .limit(limit)
        ).all()

    success = 0
    skipped = 0
    errors: list[dict[str, object]] = []
    high = medium = low = healthy = 0
    for sku_id in sku_ids:
        try:
            result = diagnose_latest_sku(int(sku_id))
            success += 1
            severity = str(result.get("severity") or "healthy")
            if severity == "high":
                high += 1
            elif severity == "medium":
                medium += 1
            elif severity == "low":
                low += 1
            else:
                healthy += 1
        except LookupError:
            skipped += 1
        except Exception as exc:
            errors.append({"sku_id": int(sku_id), "error": str(exc)})

    return {
        "ok": not errors,
        "total": len(sku_ids),
        "success": success,
        "skipped": skipped,
        "severity_counts": {
            "high": high,
            "medium": medium,
            "low": low,
            "healthy": healthy,
        },
        "errors": errors[:20],
    }


def build_ai_context(diagnosis_payload: dict[str, object]) -> str:
    return (
        "你是拼多多电商运营诊断助手。下面的数据、漏斗拆解、影响度、置信度和优先级已经由程序计算。"
        "不得修改指标、不得虚构缺失数据、不得把相关性描述成确定因果。"
        "优先围绕 priority_score 最高的问题提出动作。"
        "输出中文：先给一句经营结论，再给最多 5 条动作；每条必须包含动作、为什么、验证指标、观察周期。"
        "如果 data_quality.confidence 较低，要先明确需要补充的数据。\n\n"
        + json.dumps(diagnosis_payload, ensure_ascii=False, indent=2)
    )
