from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Shop(TimestampMixin, Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="拼多多店铺")
    platform: Mapped[str] = mapped_column(String(32), default="pinduoduo", index=True)
    owner_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    client_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    client_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list[Product]] = relationship(back_populates="shop", cascade="all, delete-orphan")


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("shop_id", "platform_goods_id", name="uq_product_shop_goods"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    platform_goods_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="")
    category_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    main_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    shop: Mapped[Shop] = relationship(back_populates="products")
    skus: Mapped[list[Sku]] = relationship(back_populates="product", cascade="all, delete-orphan")


class Sku(TimestampMixin, Base):
    __tablename__ = "skus"
    __table_args__ = (UniqueConstraint("product_id", "platform_sku_id", name="uq_sku_product_platform"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    platform_sku_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sku_name: Mapped[str] = mapped_column(String(512), default="")
    spec_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    product: Mapped[Product] = relationship(back_populates="skus")
    metrics: Mapped[list[SkuDailyMetric]] = relationship(
        back_populates="sku", cascade="all, delete-orphan"
    )


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("shop_id", "platform_order_sn", name="uq_order_shop_sn"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    platform_order_sn: Mapped[str] = mapped_column(String(128), nullable=False)
    order_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey("skus.id", ondelete="SET NULL"), index=True)
    platform_sku_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    item_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)


class Refund(TimestampMixin, Base):
    __tablename__ = "refunds"
    __table_args__ = (UniqueConstraint("shop_id", "platform_after_sales_id", name="uq_refund_shop_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    sku_id: Mapped[int | None] = mapped_column(ForeignKey("skus.id", ondelete="SET NULL"), index=True)
    platform_after_sales_id: Mapped[str] = mapped_column(String(128), nullable=False)
    platform_order_sn: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    refund_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class SkuDailyMetric(TimestampMixin, Base):
    __tablename__ = "sku_daily_metrics"
    __table_args__ = (
        UniqueConstraint("sku_id", "metric_date", name="uq_sku_metric_date"),
        Index("ix_sku_metric_date_shop", "shop_id", "metric_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), index=True)

    impression: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visitors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    sales_qty: Mapped[int] = mapped_column(Integer, default=0)
    gmv: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    refund_count: Mapped[int] = mapped_column(Integer, default=0)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    ad_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    ad_clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ad_orders: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ad_gmv: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    stock: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sku: Mapped[Sku] = relationship(back_populates="metrics")


class AIProvider(TimestampMixin, Base):
    __tablename__ = "ai_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), default="openai_compatible")
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    chat_model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    vision_model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    image_model: Mapped[str | None] = mapped_column(String(256), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class DiagnosisResult(TimestampMixin, Base):
    __tablename__ = "diagnosis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    health_score: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(32))
    diagnosis_json: Mapped[str] = mapped_column(Text)
    ai_analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class ImportJob(TimestampMixin, Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    report_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_columns_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SyncJob(TimestampMixin, Base):
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
