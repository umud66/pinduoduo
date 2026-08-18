from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.models import Shop, Sku, SkuDailyMetric
from app.services.importer.report_import import import_report


def test_import_report_creates_sku_and_metric(tmp_path: Path):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    report = tmp_path / "report.csv"
    report.write_text(
        "日期,商品ID,SKU ID,曝光量,点击量,订单数,销量,成交金额,库存\n"
        "2026-08-18,1001,2001,1000,80,10,12,478.8,35\n",
        encoding="utf-8-sig",
    )

    with Session(engine) as session:
        shop = Shop(name="测试店铺")
        session.add(shop)
        session.commit()
        summary = import_report(session, shop_id=shop.id, path=report)
        session.commit()

        assert summary.rows_imported == 1
        assert summary.skus_created == 1
        sku = session.scalar(select(Sku))
        metric = session.scalar(select(SkuDailyMetric))
        assert sku is not None
        assert sku.platform_sku_id == "2001"
        assert sku.stock == 35
        assert metric is not None
        assert metric.impression == 1000
        assert metric.clicks == 80
        assert metric.sales_qty == 12
