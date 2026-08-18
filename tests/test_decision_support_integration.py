import json
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import DiagnosisResult, Product, Sku, SkuDailyMetric
from app.services.decision_support import sku_decision_support


def test_sku_decision_support_combines_shift_change_point_and_priority() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    end = date(2026, 8, 18)

    with Session(engine) as session:
        product = Product(shop_id=1, platform_goods_id="g1", title="测试商品")
        session.add(product)
        session.flush()
        target = Sku(product_id=product.id, platform_sku_id="a", sku_name="规格 A")
        peer = Sku(product_id=product.id, platform_sku_id="b", sku_name="规格 B")
        session.add_all([target, peer])
        session.flush()

        for index in range(14):
            metric_date = end - timedelta(days=13 - index)
            recent = index >= 7
            target_gmv = Decimal("100") if recent else Decimal("200")
            peer_gmv = Decimal("200") if recent else Decimal("100")
            session.add(
                SkuDailyMetric(
                    metric_date=metric_date,
                    shop_id=1,
                    product_id=product.id,
                    sku_id=target.id,
                    impression=1000,
                    clicks=100,
                    order_count=10,
                    sales_qty=10,
                    gmv=target_gmv,
                    refund_count=0,
                    refund_amount=Decimal("0"),
                )
            )
            session.add(
                SkuDailyMetric(
                    metric_date=metric_date,
                    shop_id=1,
                    product_id=product.id,
                    sku_id=peer.id,
                    impression=1000,
                    clicks=100,
                    order_count=20,
                    sales_qty=20,
                    gmv=peer_gmv,
                    refund_count=0,
                    refund_amount=Decimal("0"),
                )
            )

        for offset in range(4):
            session.add(
                DiagnosisResult(
                    sku_id=target.id,
                    period_end=end - timedelta(days=offset),
                    health_score=65,
                    severity="high",
                    diagnosis_json=json.dumps(
                        {"issues": [{"code": "SALES_DROP", "priority_score": 72}]}
                    ),
                )
            )
        session.commit()

        result = sku_decision_support(session, target.id)
        assert result["structure_shift"]["role"] == "loser"
        assert result["structure_shift"]["cannibalization_candidate"] is True
        assert result["change_points"]["detected"] is True
        assert result["action_priority"]["base_priority"] == 72
        assert result["action_priority"]["action_priority"] > 72
        assert any(
            item["code"] == "SKU_SHIFT"
            for item in result["action_priority"]["adjustments"]
        )
