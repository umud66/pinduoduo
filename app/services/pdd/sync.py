from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal
from typing import Any, Callable

from sqlalchemy import delete, select

from app.core.secrets import SecretStore
from app.db.database import session_scope
from app.db.models import (
    Order,
    OrderItem,
    Product,
    Refund,
    Shop,
    Sku,
    SkuDailyMetric,
    SyncJob,
)
from app.db.sync_models import SyncCursor
from app.services.pdd.client import PddClient, PddCredentials
from app.services.pdd.parsers import (
    extract_goods_detail,
    extract_goods_rows,
    extract_order_detail,
    extract_order_refs,
    extract_refund_detail,
    extract_refund_rows,
    extract_sku_rows,
    first,
    page_has_more,
    to_datetime,
    to_decimal,
    to_int,
)

WINDOW_SECONDS = 30 * 60
PAGE_SIZE = 50


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def _status_text(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


class PddSyncService:
    def __init__(
        self,
        shop_id: int,
        *,
        client_factory: Callable[[PddCredentials], PddClient] = PddClient,
    ) -> None:
        self.shop_id = shop_id
        self.client_factory = client_factory
        self.secret_store = SecretStore()

    def _client(self) -> PddClient:
        with session_scope() as session:
            shop = session.get(Shop, self.shop_id)
            if shop is None:
                raise LookupError("店铺不存在")
            if not shop.client_id or not shop.client_secret_encrypted:
                raise ValueError("请先配置 Client ID 和 Client Secret")
            credentials = PddCredentials(
                client_id=shop.client_id,
                client_secret=self.secret_store.decrypt(shop.client_secret_encrypted),
                access_token=self.secret_store.decrypt(shop.access_token_encrypted or "") or None,
            )
        return self.client_factory(credentials)

    def _update_job(self, job_id: int, **stats: Any) -> None:
        with session_scope() as session:
            job = session.get(SyncJob, job_id)
            if job is None:
                return
            current: dict[str, Any] = {}
            if job.stats_json:
                try:
                    current = json.loads(job.stats_json)
                except json.JSONDecodeError:
                    current = {}
            current.update(stats)
            job.stats_json = _json(current)

    def _cursor(self, resource: str) -> int | None:
        with session_scope() as session:
            cursor = session.scalar(
                select(SyncCursor).where(
                    SyncCursor.shop_id == self.shop_id,
                    SyncCursor.resource == resource,
                )
            )
            return cursor.last_synced_at if cursor else None

    def _set_cursor(self, resource: str, timestamp: int, extra: dict[str, Any] | None = None) -> None:
        with session_scope() as session:
            cursor = session.scalar(
                select(SyncCursor).where(
                    SyncCursor.shop_id == self.shop_id,
                    SyncCursor.resource == resource,
                )
            )
            if cursor is None:
                cursor = SyncCursor(shop_id=self.shop_id, resource=resource)
                session.add(cursor)
            cursor.last_synced_at = timestamp
            cursor.extra_json = _json(extra or {})

    def sync_products(self, job_id: int) -> dict[str, int]:
        client = self._client()
        page = 1
        seen = 0
        products_created = 0
        products_updated = 0
        skus_created = 0
        skus_updated = 0

        while True:
            payload = client.goods_list(page=page, page_size=PAGE_SIZE)
            rows = extract_goods_rows(payload)
            self._update_job(job_id, stage="products", page=page, discovered=seen + len(rows))
            if not rows:
                break

            for stub in rows:
                goods_id = first(stub, "goods_id", "id")
                if goods_id in (None, ""):
                    continue
                detail_payload = client.goods_detail(goods_id)
                detail = extract_goods_detail(detail_payload) or stub
                result = self._upsert_product(goods_id, detail, detail_payload)
                products_created += result["products_created"]
                products_updated += result["products_updated"]
                skus_created += result["skus_created"]
                skus_updated += result["skus_updated"]
                seen += 1

            if not page_has_more(payload, page=page, page_size=PAGE_SIZE, row_count=len(rows)):
                break
            page += 1

        now = int(time.time())
        self._set_cursor("products", now, {"count": seen})
        return {
            "products": seen,
            "products_created": products_created,
            "products_updated": products_updated,
            "skus_created": skus_created,
            "skus_updated": skus_updated,
        }

    def _upsert_product(
        self,
        goods_id: int | str,
        detail: dict[str, Any],
        raw_payload: dict[str, Any],
    ) -> dict[str, int]:
        result = {"products_created": 0, "products_updated": 0, "skus_created": 0, "skus_updated": 0}
        with session_scope() as session:
            platform_goods_id = str(first(detail, "goods_id", default=goods_id))
            product = session.scalar(
                select(Product).where(
                    Product.shop_id == self.shop_id,
                    Product.platform_goods_id == platform_goods_id,
                )
            )
            if product is None:
                product = Product(shop_id=self.shop_id, platform_goods_id=platform_goods_id)
                session.add(product)
                session.flush()
                result["products_created"] += 1
            else:
                result["products_updated"] += 1

            product.title = str(first(detail, "goods_name", "title", "goods_desc", default=product.title or ""))
            product.category_id = _status_text(first(detail, "cat_id", "category_id", "goods_category_id"))
            product.status = _status_text(first(detail, "goods_status", "status", "is_onsale"))
            product.main_image = _status_text(first(detail, "thumb_url", "goods_image_url", "image_url", "hd_thumb_url", default=product.main_image))
            product.raw_json = _json(raw_payload)

            for sku_raw in extract_sku_rows(detail):
                raw_sku_id = first(sku_raw, "sku_id", "id")
                if raw_sku_id in (None, ""):
                    continue
                sku_id = str(raw_sku_id)
                sku = session.scalar(
                    select(Sku).where(Sku.product_id == product.id, Sku.platform_sku_id == sku_id)
                )
                if sku is None:
                    sku = Sku(product_id=product.id, platform_sku_id=sku_id)
                    session.add(sku)
                    result["skus_created"] += 1
                else:
                    result["skus_updated"] += 1

                spec = first(sku_raw, "spec", "spec_key", "specs", "specifications", default="")
                sku.sku_name = spec if isinstance(spec, str) else _json(spec)
                sku.spec_json = _json(spec) if isinstance(spec, (dict, list)) else None
                sku.image_url = _status_text(first(sku_raw, "thumb_url", "sku_img", "image_url"))
                sku.price = to_decimal(first(sku_raw, "group_price", "price", "normal_price", "market_price"), integer_is_cents=True)
                sku.stock = to_int(first(sku_raw, "goods_quantity", "quantity", "stock", "sku_quantity"))
                sku.status = _status_text(first(sku_raw, "is_onsale", "status", "sku_status"))
        return result

    def sync_historical_orders(self, job_id: int, *, lookback_days: int = 30) -> dict[str, int]:
        client = self._client()
        now = int(time.time())
        start = now - max(1, min(90, lookback_days)) * 86400
        affected_dates: set[date] = set()
        processed = created = updated = 0

        window_start = start
        while window_start < now:
            window_end = min(window_start + 86400 - 1, now)
            page = 1
            while True:
                payload = client.order_list(start_confirm_at=window_start, end_confirm_at=window_end, page=page, page_size=PAGE_SIZE)
                refs = extract_order_refs(payload)
                if not refs:
                    break
                for raw in refs:
                    order_sn = str(first(raw, "order_sn", default=""))
                    detail = raw
                    if order_sn and not isinstance(first(raw, "goods_list", "item_list", "order_items"), list):
                        detail = extract_order_detail(client.order_information(order_sn)) or raw
                    result = self._upsert_order(detail)
                    processed += result["processed"]
                    created += result["created"]
                    updated += result["updated"]
                    affected_dates.update(result["dates"])
                self._update_job(job_id, stage="orders", mode="historical", window_end=window_end, page=page, processed=processed)
                if not page_has_more(payload, page=page, page_size=PAGE_SIZE, row_count=len(refs)):
                    break
                page += 1
            window_start = window_end + 1

        self._set_cursor("orders", now, {"mode": "historical", "lookback_days": lookback_days})
        rebuild_commerce_metrics(self.shop_id, affected_dates)
        return {"orders": processed, "created": created, "updated": updated}

    def sync_incremental_orders(self, job_id: int, *, lookback_days: int = 7) -> dict[str, int]:
        client = self._client()
        now = int(time.time())
        cursor = self._cursor("orders")
        start = cursor if cursor else now - max(1, lookback_days) * 86400
        affected_dates: set[date] = set()
        processed = created = updated = 0

        window_start = start
        while window_start < now:
            window_end = min(window_start + WINDOW_SECONDS - 1, now)
            page = 1
            while True:
                payload = client.order_increment(start_updated_at=window_start, end_updated_at=window_end, page=page, page_size=PAGE_SIZE)
                refs = extract_order_refs(payload)
                if not refs:
                    break
                for raw in refs:
                    order_sn = str(first(raw, "order_sn", default=""))
                    if not order_sn:
                        continue
                    detail = extract_order_detail(client.order_information(order_sn))
                    if not detail:
                        continue
                    result = self._upsert_order(detail)
                    processed += result["processed"]
                    created += result["created"]
                    updated += result["updated"]
                    affected_dates.update(result["dates"])
                self._update_job(job_id, stage="orders", mode="incremental", window_end=window_end, page=page, processed=processed)
                if not page_has_more(payload, page=page, page_size=PAGE_SIZE, row_count=len(refs)):
                    break
                page += 1
            window_start = window_end + 1

        self._set_cursor("orders", now, {"mode": "incremental"})
        rebuild_commerce_metrics(self.shop_id, affected_dates)
        return {"orders": processed, "created": created, "updated": updated}

    def _upsert_order(self, detail: dict[str, Any]) -> dict[str, Any]:
        order_sn = str(first(detail, "order_sn", default="")).strip()
        if not order_sn:
            return {"processed": 0, "created": 0, "updated": 0, "dates": set()}

        paid_at = to_datetime(first(detail, "pay_time", "confirm_time", "created_time", "order_time"))
        dates = {paid_at.date()} if paid_at else set()
        created = updated = 0
        with session_scope() as session:
            order = session.scalar(select(Order).where(Order.shop_id == self.shop_id, Order.platform_order_sn == order_sn))
            if order is None:
                order = Order(shop_id=self.shop_id, platform_order_sn=order_sn)
                session.add(order)
                session.flush()
                created = 1
            else:
                updated = 1

            order.order_status = _status_text(first(detail, "order_status", "order_status_str", "status"))
            order.order_amount = to_decimal(first(detail, "order_amount", "pay_amount", "amount"), integer_is_cents=True)
            order.paid_at = paid_at
            order.raw_json = _json(detail)

            session.execute(delete(OrderItem).where(OrderItem.order_id == order.id))
            items = first(detail, "goods_list", "item_list", "order_items", default=[])
            if not isinstance(items, list):
                items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                platform_sku_id = first(item, "sku_id", "outer_id")
                sku = self._find_sku(session, platform_sku_id)
                quantity = to_int(first(item, "goods_count", "quantity", "goods_number")) or 1
                amount = to_decimal(first(item, "goods_amount", "item_amount", "goods_price", "price"), integer_is_cents=True)
                if amount is not None and first(item, "goods_amount", "item_amount") in (None, ""):
                    amount *= quantity
                session.add(OrderItem(order_id=order.id, sku_id=sku.id if sku else None, platform_sku_id=str(platform_sku_id) if platform_sku_id is not None else None, quantity=quantity, item_amount=amount))
        return {"processed": 1, "created": created, "updated": updated, "dates": dates}

    def sync_refunds(self, job_id: int, *, lookback_days: int = 7) -> dict[str, int]:
        client = self._client()
        now = int(time.time())
        cursor = self._cursor("refunds")
        start = cursor if cursor else now - max(1, lookback_days) * 86400
        affected_dates: set[date] = set()
        processed = created = updated = 0

        window_start = start
        while window_start < now:
            window_end = min(window_start + WINDOW_SECONDS - 1, now)
            page = 1
            while True:
                payload = client.refund_increment(start_updated_at=window_start, end_updated_at=window_end, page=page, page_size=PAGE_SIZE)
                rows = extract_refund_rows(payload)
                if not rows:
                    break
                for raw in rows:
                    after_sales_id = first(raw, "after_sales_id", "id")
                    detail = raw
                    if after_sales_id not in (None, ""):
                        try:
                            fetched = extract_refund_detail(client.refund_information(after_sales_id))
                            if fetched:
                                detail = fetched
                        except Exception:
                            detail = raw
                    result = self._upsert_refund(detail)
                    processed += result["processed"]
                    created += result["created"]
                    updated += result["updated"]
                    affected_dates.update(result["dates"])
                self._update_job(job_id, stage="refunds", window_end=window_end, page=page, processed=processed)
                if not page_has_more(payload, page=page, page_size=PAGE_SIZE, row_count=len(rows)):
                    break
                page += 1
            window_start = window_end + 1

        self._set_cursor("refunds", now, {"mode": "incremental"})
        rebuild_commerce_metrics(self.shop_id, affected_dates)
        return {"refunds": processed, "created": created, "updated": updated}

    def _upsert_refund(self, detail: dict[str, Any]) -> dict[str, Any]:
        after_sales_id = first(detail, "after_sales_id", "id")
        if after_sales_id in (None, ""):
            return {"processed": 0, "created": 0, "updated": 0, "dates": set()}

        occurred_at = to_datetime(first(detail, "updated_at", "created_at", "after_sales_create_time", "refund_time"))
        dates = {occurred_at.date()} if occurred_at else set()
        created = updated = 0
        with session_scope() as session:
            refund = session.scalar(select(Refund).where(Refund.shop_id == self.shop_id, Refund.platform_after_sales_id == str(after_sales_id)))
            if refund is None:
                refund = Refund(shop_id=self.shop_id, platform_after_sales_id=str(after_sales_id))
                session.add(refund)
                created = 1
            else:
                updated = 1

            platform_sku_id = first(detail, "sku_id", "outer_id")
            sku = self._find_sku(session, platform_sku_id)
            refund.sku_id = sku.id if sku else None
            refund.platform_order_sn = _status_text(first(detail, "order_sn"))
            refund.refund_status = _status_text(first(detail, "after_sales_status", "refund_status", "status"))
            refund.refund_amount = to_decimal(first(detail, "refund_amount", "after_sales_amount", "amount"), integer_is_cents=True)
            refund.occurred_at = occurred_at
            refund.raw_json = _json(detail)
        return {"processed": 1, "created": created, "updated": updated, "dates": dates}

    def _find_sku(self, session, platform_sku_id: Any) -> Sku | None:
        if platform_sku_id in (None, ""):
            return None
        return session.scalar(
            select(Sku)
            .join(Product, Sku.product_id == Product.id)
            .where(Product.shop_id == self.shop_id, Sku.platform_sku_id == str(platform_sku_id))
            .limit(1)
        )

    def sync_full(self, job_id: int, *, lookback_days: int = 30) -> dict[str, Any]:
        self._update_job(job_id, stage="products", mode="full")
        products = self.sync_products(job_id)
        self._update_job(job_id, stage="orders", mode="full")
        orders = self.sync_historical_orders(job_id, lookback_days=lookback_days)
        self._update_job(job_id, stage="refunds", mode="full")
        refunds = self.sync_refunds(job_id, lookback_days=lookback_days)
        return {"products": products, "orders": orders, "refunds": refunds}

    def sync_incremental(self, job_id: int) -> dict[str, Any]:
        self._update_job(job_id, stage="orders", mode="incremental")
        orders = self.sync_incremental_orders(job_id)
        self._update_job(job_id, stage="refunds", mode="incremental")
        refunds = self.sync_refunds(job_id)
        return {"orders": orders, "refunds": refunds}


def rebuild_commerce_metrics(shop_id: int, affected_dates: set[date]) -> None:
    if not affected_dates:
        return

    min_date = min(affected_dates)
    max_date = max(affected_dates)
    start_dt = datetime.combine(min_date, dt_time.min)
    end_dt = datetime.combine(max_date + timedelta(days=1), dt_time.min)

    order_sets: dict[tuple[int, date], set[int]] = defaultdict(set)
    sales_qty: dict[tuple[int, date], int] = defaultdict(int)
    gmv: dict[tuple[int, date], Decimal] = defaultdict(lambda: Decimal("0"))
    refund_count: dict[tuple[int, date], int] = defaultdict(int)
    refund_amount: dict[tuple[int, date], Decimal] = defaultdict(lambda: Decimal("0"))

    with session_scope() as session:
        order_rows = session.execute(
            select(OrderItem, Order)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.shop_id == shop_id, Order.paid_at >= start_dt, Order.paid_at < end_dt, OrderItem.sku_id.is_not(None))
        ).all()
        for item, order in order_rows:
            if not order.paid_at or item.sku_id is None:
                continue
            metric_date = order.paid_at.date()
            if metric_date not in affected_dates:
                continue
            key = (item.sku_id, metric_date)
            order_sets[key].add(order.id)
            sales_qty[key] += item.quantity or 0
            gmv[key] += Decimal(item.item_amount or 0)

        refund_rows = session.scalars(
            select(Refund).where(Refund.shop_id == shop_id, Refund.occurred_at >= start_dt, Refund.occurred_at < end_dt, Refund.sku_id.is_not(None))
        ).all()
        for refund in refund_rows:
            if not refund.occurred_at or refund.sku_id is None:
                continue
            metric_date = refund.occurred_at.date()
            if metric_date not in affected_dates:
                continue
            key = (refund.sku_id, metric_date)
            refund_count[key] += 1
            refund_amount[key] += Decimal(refund.refund_amount or 0)

        sku_ids = {key[0] for key in set(order_sets) | set(sales_qty) | set(gmv) | set(refund_count) | set(refund_amount)}
        sku_map = {sku.id: sku for sku in session.scalars(select(Sku).where(Sku.id.in_(sku_ids or {-1}))).all()}
        all_keys = set(order_sets) | set(sales_qty) | set(gmv) | set(refund_count) | set(refund_amount)
        for sku_id, metric_date in all_keys:
            sku = sku_map.get(sku_id)
            if sku is None:
                continue
            product = session.get(Product, sku.product_id)
            if product is None:
                continue
            metric = session.scalar(select(SkuDailyMetric).where(SkuDailyMetric.sku_id == sku_id, SkuDailyMetric.metric_date == metric_date))
            if metric is None:
                metric = SkuDailyMetric(metric_date=metric_date, shop_id=shop_id, product_id=product.id, sku_id=sku_id)
                session.add(metric)
            metric.order_count = len(order_sets.get((sku_id, metric_date), set()))
            metric.sales_qty = sales_qty.get((sku_id, metric_date), 0)
            metric.gmv = gmv.get((sku_id, metric_date), Decimal("0"))
            metric.refund_count = refund_count.get((sku_id, metric_date), 0)
            metric.refund_amount = refund_amount.get((sku_id, metric_date), Decimal("0"))
            if sku.price is not None:
                metric.price = sku.price
            if sku.stock is not None:
                metric.stock = sku.stock
