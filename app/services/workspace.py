from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AIProvider, DiagnosisResult, Product, Shop, Sku, SkuDailyMetric


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _metric_payload(metric: SkuDailyMetric | None) -> dict[str, object] | None:
    if metric is None:
        return None
    impression = metric.impression
    clicks = metric.clicks
    orders = metric.order_count or 0
    return {
        "date": metric.metric_date.isoformat(),
        "impression": impression,
        "visitors": metric.visitors,
        "clicks": clicks,
        "order_count": orders,
        "sales_qty": metric.sales_qty or 0,
        "gmv": _number(metric.gmv),
        "refund_count": metric.refund_count or 0,
        "refund_amount": _number(metric.refund_amount),
        "ad_cost": _number(metric.ad_cost) if metric.ad_cost is not None else None,
        "ad_gmv": _number(metric.ad_gmv) if metric.ad_gmv is not None else None,
        "price": _number(metric.price) if metric.price is not None else None,
        "stock": metric.stock,
        "ctr": (clicks / impression) if impression and clicks is not None else None,
        "cvr": (orders / clicks) if clicks else None,
        "refund_rate": ((metric.refund_count or 0) / orders) if orders else None,
        "ad_roi": (_number(metric.ad_gmv) / _number(metric.ad_cost))
        if metric.ad_cost and metric.ad_gmv is not None
        else None,
    }


def _latest_metric(session: Session, sku_id: int) -> SkuDailyMetric | None:
    return session.scalar(
        select(SkuDailyMetric)
        .where(SkuDailyMetric.sku_id == sku_id)
        .order_by(SkuDailyMetric.metric_date.desc())
        .limit(1)
    )


def _latest_diagnosis(session: Session, sku_id: int) -> DiagnosisResult | None:
    return session.scalar(
        select(DiagnosisResult)
        .where(DiagnosisResult.sku_id == sku_id)
        .order_by(DiagnosisResult.period_end.desc(), DiagnosisResult.id.desc())
        .limit(1)
    )


def bootstrap_status(session: Session) -> dict[str, object]:
    shop_count = session.scalar(select(func.count()).select_from(Shop)) or 0
    provider_count = session.scalar(select(func.count()).select_from(AIProvider)) or 0
    sku_count = session.scalar(select(func.count()).select_from(Sku)) or 0
    metric_count = session.scalar(select(func.count()).select_from(SkuDailyMetric)) or 0
    return {
        "setup_complete": shop_count > 0,
        "shop_count": shop_count,
        "provider_count": provider_count,
        "sku_count": sku_count,
        "metric_count": metric_count,
        "next_action": (
            "create_shop"
            if shop_count == 0
            else "import_data"
            if metric_count == 0
            else "configure_ai"
            if provider_count == 0
            else "ready"
        ),
    }


def dashboard_summary(session: Session, shop_id: int) -> dict[str, object]:
    shop = session.get(Shop, shop_id)
    if shop is None:
        raise LookupError("店铺不存在")

    latest_date = session.scalar(
        select(func.max(SkuDailyMetric.metric_date)).where(SkuDailyMetric.shop_id == shop_id)
    )
    if latest_date is None:
        return {
            "shop": {"id": shop.id, "name": shop.name},
            "latest_date": None,
            "metrics": {},
            "changes": {},
            "urgent_skus": [],
            "trend": [],
            "data_state": "empty",
        }

    start_date = latest_date - timedelta(days=13)
    rows = session.scalars(
        select(SkuDailyMetric)
        .where(
            SkuDailyMetric.shop_id == shop_id,
            SkuDailyMetric.metric_date >= start_date,
            SkuDailyMetric.metric_date <= latest_date,
        )
        .order_by(SkuDailyMetric.metric_date)
    ).all()

    daily: dict[date, dict[str, float]] = defaultdict(
        lambda: {"gmv": 0.0, "sales_qty": 0.0, "order_count": 0.0, "refund_count": 0.0}
    )
    for row in rows:
        bucket = daily[row.metric_date]
        bucket["gmv"] += _number(row.gmv)
        bucket["sales_qty"] += float(row.sales_qty or 0)
        bucket["order_count"] += float(row.order_count or 0)
        bucket["refund_count"] += float(row.refund_count or 0)

    current = daily[latest_date]
    baseline_dates = [latest_date - timedelta(days=i) for i in range(1, 8)]
    baseline_values = [daily[d] for d in baseline_dates if d in daily]

    def avg(field: str) -> float:
        if not baseline_values:
            return 0.0
        return sum(item[field] for item in baseline_values) / len(baseline_values)

    def change(field: str) -> float | None:
        base = avg(field)
        if base <= 0:
            return None
        return (current[field] - base) / base

    refund_rate = (
        current["refund_count"] / current["order_count"] if current["order_count"] > 0 else None
    )

    sku_count = session.scalar(
        select(func.count()).select_from(Sku).join(Product).where(Product.shop_id == shop_id)
    ) or 0
    product_count = session.scalar(select(func.count()).select_from(Product).where(Product.shop_id == shop_id)) or 0

    sku_rows = session.execute(
        select(Sku, Product)
        .join(Product, Sku.product_id == Product.id)
        .where(Product.shop_id == shop_id)
        .order_by(Sku.id)
    ).all()
    urgent: list[dict[str, object]] = []
    severity_rank = {"high": 3, "medium": 2, "low": 1, "healthy": 0}
    for sku, product in sku_rows:
        diag = _latest_diagnosis(session, sku.id)
        if diag is None or diag.severity == "healthy":
            continue
        payload = json.loads(diag.diagnosis_json)
        first_issue = (payload.get("issues") or [{}])[0]
        urgent.append(
            {
                "sku_id": sku.id,
                "sku_name": sku.sku_name or sku.platform_sku_id,
                "product_title": product.title,
                "health_score": diag.health_score,
                "severity": diag.severity,
                "issue": first_issue.get("title") or "存在经营异常",
            }
        )
    urgent.sort(key=lambda item: (-severity_rank.get(str(item["severity"]), 0), item["health_score"]))

    trend = []
    for metric_date in sorted(daily):
        item = daily[metric_date]
        trend.append(
            {
                "date": metric_date.isoformat(),
                "gmv": round(item["gmv"], 2),
                "sales_qty": int(item["sales_qty"]),
                "order_count": int(item["order_count"]),
            }
        )

    return {
        "shop": {"id": shop.id, "name": shop.name},
        "latest_date": latest_date.isoformat(),
        "metrics": {
            "gmv": round(current["gmv"], 2),
            "sales_qty": int(current["sales_qty"]),
            "order_count": int(current["order_count"]),
            "refund_rate": refund_rate,
            "product_count": product_count,
            "sku_count": sku_count,
        },
        "changes": {
            "gmv": change("gmv"),
            "sales_qty": change("sales_qty"),
            "order_count": change("order_count"),
        },
        "urgent_skus": urgent[:8],
        "trend": trend,
        "data_state": "ready",
    }


def list_skus(
    session: Session,
    *,
    shop_id: int,
    query: str = "",
    severity: str = "all",
) -> list[dict[str, object]]:
    statement = (
        select(Sku, Product)
        .join(Product, Sku.product_id == Product.id)
        .where(Product.shop_id == shop_id)
        .order_by(Product.id, Sku.id)
    )
    pairs = session.execute(statement).all()
    needle = query.strip().lower()
    result: list[dict[str, object]] = []
    for sku, product in pairs:
        if needle and needle not in " ".join(
            [product.title or "", sku.sku_name or "", sku.platform_sku_id or "", product.platform_goods_id or ""]
        ).lower():
            continue
        metric = _latest_metric(session, sku.id)
        diag = _latest_diagnosis(session, sku.id)
        diag_severity = diag.severity if diag else "unrun"
        if severity != "all" and diag_severity != severity:
            continue
        diag_payload = json.loads(diag.diagnosis_json) if diag else None
        result.append(
            {
                "id": sku.id,
                "platform_sku_id": sku.platform_sku_id,
                "sku_name": sku.sku_name or sku.platform_sku_id,
                "product_id": product.id,
                "platform_goods_id": product.platform_goods_id,
                "product_title": product.title,
                "image_url": sku.image_url or product.main_image,
                "price": _number(sku.price) if sku.price is not None else None,
                "stock": sku.stock,
                "metric": _metric_payload(metric),
                "diagnosis": {
                    "id": diag.id,
                    "health_score": diag.health_score,
                    "severity": diag.severity,
                    "issue_count": len(diag_payload.get("issues", [])) if diag_payload else 0,
                    "main_issue": ((diag_payload.get("issues") or [{}])[0].get("title") if diag_payload else None),
                    "period_end": diag.period_end.isoformat(),
                }
                if diag
                else None,
            }
        )

    def sales(item: dict[str, object]) -> int:
        metric = item.get("metric") or {}
        return int(metric.get("sales_qty") or 0) if isinstance(metric, dict) else 0

    result.sort(key=lambda item: sales(item), reverse=True)
    return result


def sku_detail(session: Session, sku_id: int) -> dict[str, object]:
    sku = session.get(Sku, sku_id)
    if sku is None:
        raise LookupError("SKU 不存在")
    product = session.get(Product, sku.product_id)
    metrics = session.scalars(
        select(SkuDailyMetric)
        .where(SkuDailyMetric.sku_id == sku_id)
        .order_by(SkuDailyMetric.metric_date.desc())
        .limit(30)
    ).all()
    diagnosis = _latest_diagnosis(session, sku_id)
    diag_payload = json.loads(diagnosis.diagnosis_json) if diagnosis else None
    return {
        "id": sku.id,
        "platform_sku_id": sku.platform_sku_id,
        "sku_name": sku.sku_name or sku.platform_sku_id,
        "price": _number(sku.price) if sku.price is not None else None,
        "stock": sku.stock,
        "image_url": sku.image_url or (product.main_image if product else None),
        "product": {
            "id": product.id,
            "platform_goods_id": product.platform_goods_id,
            "title": product.title,
        }
        if product
        else None,
        "latest_metric": _metric_payload(metrics[0] if metrics else None),
        "metrics": [_metric_payload(item) for item in reversed(metrics)],
        "diagnosis": {
            **(diag_payload or {}),
            "id": diagnosis.id,
            "ai_analysis": json.loads(diagnosis.ai_analysis_json)
            if diagnosis and diagnosis.ai_analysis_json
            else None,
        }
        if diagnosis
        else None,
    }


def seed_demo_data(session: Session, shop_id: int) -> dict[str, object]:
    shop = session.get(Shop, shop_id)
    if shop is None:
        raise LookupError("店铺不存在")

    products = [
        ("demo-goods-001", "夏季轻薄防晒外套", [("demo-sku-001", "冰川灰 / M"), ("demo-sku-002", "冰川灰 / L")]),
        ("demo-goods-002", "厨房强力去油湿巾", [("demo-sku-003", "80抽 / 3包装"), ("demo-sku-004", "80抽 / 5包装")]),
        ("demo-goods-003", "大容量保温吸管杯", [("demo-sku-005", "奶油白 1200ml"), ("demo-sku-006", "樱花粉 1200ml")]),
    ]
    sku_records: list[Sku] = []
    for goods_id, title, skus in products:
        product = session.scalar(
            select(Product).where(Product.shop_id == shop_id, Product.platform_goods_id == goods_id)
        )
        if product is None:
            product = Product(
                shop_id=shop_id,
                platform_goods_id=goods_id,
                title=title,
                status="demo",
            )
            session.add(product)
            session.flush()
        for sku_external_id, sku_name in skus:
            sku = session.scalar(
                select(Sku).where(
                    Sku.product_id == product.id,
                    Sku.platform_sku_id == sku_external_id,
                )
            )
            if sku is None:
                sku = Sku(
                    product_id=product.id,
                    platform_sku_id=sku_external_id,
                    sku_name=sku_name,
                    price=Decimal("39.90"),
                    stock=120,
                    status="demo",
                )
                session.add(sku)
                session.flush()
            sku_records.append(sku)

    today = date.today()
    patterns = [
        (18, 1600, 120, 17, 1, 80, 38, 160),
        (16, 1500, 110, 15, 1, 70, 35, 145),
        (20, 1750, 130, 18, 1, 95, 40, 178),
        (14, 1420, 105, 13, 0, 64, 32, 125),
        (19, 1680, 126, 17, 1, 76, 36, 166),
        (17, 1580, 119, 16, 1, 69, 34, 151),
        (18, 1650, 123, 17, 1, 62, 37, 158),
    ]
    current_variants = [
        (7, 1700, 49, 7, 0, 54, 39, 80),
        (15, 1560, 116, 14, 1, 2, 34, 142),
        (14, 1490, 108, 13, 4, 96, 36, 126),
        (17, 1620, 121, 16, 1, 88, 41, 142),
        (5, 1510, 112, 5, 0, 74, 35, 72),
        (16, 1600, 122, 15, 1, 68, 55, 35),
    ]

    created = 0
    for index, sku in enumerate(sku_records):
        product = session.get(Product, sku.product_id)
        for offset in range(7, 0, -1):
            metric_date = today - timedelta(days=offset)
            values = patterns[(7 - offset + index) % len(patterns)]
            existing = session.scalar(
                select(SkuDailyMetric).where(
                    SkuDailyMetric.sku_id == sku.id,
                    SkuDailyMetric.metric_date == metric_date,
                )
            )
            if existing is not None:
                continue
            sales, impressions, clicks, orders, refunds, stock, ad_cost, ad_gmv = values
            session.add(
                SkuDailyMetric(
                    metric_date=metric_date,
                    shop_id=shop_id,
                    product_id=product.id,
                    sku_id=sku.id,
                    impression=impressions,
                    visitors=max(clicks + 12, clicks),
                    clicks=clicks,
                    order_count=orders,
                    sales_qty=sales,
                    gmv=Decimal(str(sales * 39.9)),
                    refund_count=refunds,
                    refund_amount=Decimal(str(refunds * 39.9)),
                    ad_cost=Decimal(str(ad_cost)),
                    ad_clicks=max(1, clicks // 3),
                    ad_orders=max(1, orders // 3),
                    ad_gmv=Decimal(str(ad_gmv)),
                    price=Decimal("39.90"),
                    stock=stock,
                )
            )
            created += 1

        current = session.scalar(
            select(SkuDailyMetric).where(
                SkuDailyMetric.sku_id == sku.id,
                SkuDailyMetric.metric_date == today,
            )
        )
        if current is None:
            sales, impressions, clicks, orders, refunds, stock, ad_cost, ad_gmv = current_variants[index]
            current = SkuDailyMetric(
                metric_date=today,
                shop_id=shop_id,
                product_id=product.id,
                sku_id=sku.id,
                impression=impressions,
                visitors=max(clicks + 10, clicks),
                clicks=clicks,
                order_count=orders,
                sales_qty=sales,
                gmv=Decimal(str(sales * 39.9)),
                refund_count=refunds,
                refund_amount=Decimal(str(refunds * 39.9)),
                ad_cost=Decimal(str(ad_cost)),
                ad_clicks=max(1, clicks // 3),
                ad_orders=max(1, orders // 3),
                ad_gmv=Decimal(str(ad_gmv)),
                price=Decimal("39.90"),
                stock=stock,
            )
            session.add(current)
            sku.stock = stock
            created += 1

    return {"ok": True, "sku_count": len(sku_records), "metric_rows_created": created}
