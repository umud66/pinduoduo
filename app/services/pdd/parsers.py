from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable


def _walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_dicts(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_dicts(nested)


def find_list(payload: dict[str, Any], keys: tuple[str, ...]) -> list[Any]:
    for obj in _walk_dicts(payload):
        for key in keys:
            value = obj.get(key)
            if isinstance(value, list):
                return value
    return []


def find_dict(payload: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    for obj in _walk_dicts(payload):
        for key in keys:
            value = obj.get(key)
            if isinstance(value, dict):
                return value
    return {}


def first(source: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value
    return default


def to_decimal(value: Any, *, integer_is_cents: bool = False) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and integer_is_cents:
            return Decimal(value) / Decimal(100)
        text = str(value).strip()
        if not text:
            return None
        if integer_is_cents and re_is_integer(text):
            return Decimal(text) / Decimal(100)
        return Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return None


def re_is_integer(value: str) -> bool:
    return value.lstrip("-").isdigit()


def to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def to_datetime(value: Any) -> datetime | None:
    if value in (None, "", 0, "0"):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value))
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if text.isdigit():
        try:
            return datetime.fromtimestamp(int(text))
        except (OverflowError, OSError, ValueError):
            return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None


def extract_goods_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = find_list(payload, ("goods_list", "goods_infos", "goods_info_list"))
    return [row for row in rows if isinstance(row, dict)]


def extract_goods_detail(payload: dict[str, Any]) -> dict[str, Any]:
    detail = find_dict(payload, ("goods_detail", "goods_info"))
    if detail:
        return detail
    for obj in _walk_dicts(payload):
        if any(key in obj for key in ("goods_id", "goods_name", "sku_list")):
            return obj
    return {}


def extract_order_refs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = find_list(payload, ("order_sn_list", "order_list", "order_info_list"))
    result: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, str):
            result.append({"order_sn": row})
        elif isinstance(row, dict):
            result.append(row)
    return result


def extract_order_detail(payload: dict[str, Any]) -> dict[str, Any]:
    detail = find_dict(payload, ("order_info", "order_detail"))
    if detail:
        return detail
    for obj in _walk_dicts(payload):
        if "order_sn" in obj and any(key in obj for key in ("goods_list", "order_amount", "pay_time")):
            return obj
    return {}


def extract_refund_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = find_list(payload, ("refund_list", "after_sales_list", "refund_info_list"))
    return [row for row in rows if isinstance(row, dict)]


def extract_refund_detail(payload: dict[str, Any]) -> dict[str, Any]:
    detail = find_dict(payload, ("refund_info", "after_sales_info"))
    if detail:
        return detail
    for obj in _walk_dicts(payload):
        if any(key in obj for key in ("after_sales_id", "id")) and "order_sn" in obj:
            return obj
    return {}


def extract_sku_rows(goods_detail: dict[str, Any]) -> list[dict[str, Any]]:
    value = first(goods_detail, "sku_list", "sku_infos", "skus", default=[])
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def page_has_more(payload: dict[str, Any], *, page: int, page_size: int, row_count: int) -> bool:
    total = None
    for obj in _walk_dicts(payload):
        total = first(obj, "total_count", "total", "total_num")
        if total is not None:
            break
    total_int = to_int(total)
    if total_int is not None:
        return page * page_size < total_int
    return row_count >= page_size
