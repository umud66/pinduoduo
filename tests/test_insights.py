import json
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import DiagnosisResult, Product, Shop, Sku, SkuDailyMetric
from app.services.insights import shop_trend_overview, sku_insights


def test_sku_insights_combines_windows_peers_and_persistence() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    end = date(2026, 8, 18)

    with Session(engine) as session:
        shop = Shop(name="趋势测试店")
        session.add(shop)
        session.flush()
        product = Product(shop_id=shop.id, platform_goods_id="g-1", title="测试商品")
        session.add(product)
        session.flush()
        target = Sku(product_id=product.id, platform_sku_id="s-1", sku_name="规格 A")
        peer = Sku(product_id=product.id, platform_sku_id="s-2", sku_name="规格 B")
        session.add_all([target, peer])
        session.flush()

        for index in range(14):
            metric_date = end - timedelta(days=13 - index)
            recent = index >= 7
            session.add(
                SkuDailyMetric(
                    metric_date=metric_date,
                    shop_id=shop.id,
                    product_id=product.id,
                    sku_id=target.id,
                    impression=1000,
                    clicks=100,
                    order_count=10 if recent else 20,
                    sales_qty=10 if recent else 20,
                    gmv=Decimal("100") if recent else Decimal("200"),
                    refund_count=1,
                    refund_amount=Decimal("10"),
                    ad_cost=Decimal("20"),
                    ad_gmv=Decimal("50"),
                    price=Decimal("10"),
                    stock=100,
                )
            )
            session.add(
                SkuDailyMetric(
                    metric_date=metric_date,
                    shop_id=shop.id,
                    product_id=product.id,
                    sku_id=peer.id,
                    impression=1000,
                    clicks=100,
                    order_count=20,
                    sales_qty=20,
                    gmv=Decimal("200"),
                    refund_count=1,
                    refund_amount=Decimal("10"),
                    ad_cost=Decimal("20"),
                    ad_gmv=Decimal("50"),
                    price=Decimal("10"),
                    stock=100,
                )
            )

        for offset in range(3):
            session.add(
                DiagnosisResult(
                    sku_id=target.id,
                    period_end=end - timedelta(days=offset),
                    health_score=70,
                    severity="medium",
                    diagnosis_json=json.dumps({"issues": [{"code": "SALES_DROP"}]}),
                )
            )
        session.commit()

        result = sku_insights(session, target.id)
        assert result["window_comparison"]["week_over_week"]["gmv"]["change"] == -0.5
        assert result["peer_comparison"]["target"]["rank"] == 2
        assert result["persistence"]["max_consecutive_days"] == 3

        overview = shop_trend_overview(session, shop.id)
        assert overview["summary"]["down"] == 1
        assert overview["top_decliners"][0]["sku_id"] == target.id
