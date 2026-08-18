from app.services.pdd.parsers import (
    extract_goods_detail,
    extract_goods_rows,
    extract_order_detail,
    extract_order_refs,
    extract_refund_rows,
    extract_sku_rows,
    page_has_more,
    to_decimal,
)


def test_extract_goods_and_skus_from_nested_response():
    payload = {
        "goods_list_get_response": {
            "total_count": 1,
            "goods_list": [{"goods_id": 123, "goods_name": "测试商品"}],
        }
    }
    assert extract_goods_rows(payload)[0]["goods_id"] == 123

    detail_payload = {
        "goods_detail_get_response": {
            "goods_detail": {
                "goods_id": 123,
                "sku_list": [{"sku_id": 456, "spec": "黑色"}],
            }
        }
    }
    detail = extract_goods_detail(detail_payload)
    assert detail["goods_id"] == 123
    assert extract_sku_rows(detail)[0]["sku_id"] == 456


def test_extract_order_refs_and_detail():
    increment = {
        "order_sn_list_get_response": {
            "order_sn_list": [{"order_sn": "240101-123"}]
        }
    }
    assert extract_order_refs(increment) == [{"order_sn": "240101-123"}]

    detail_payload = {
        "order_info_get_response": {
            "order_info": {
                "order_sn": "240101-123",
                "goods_list": [{"sku_id": 9}],
            }
        }
    }
    assert extract_order_detail(detail_payload)["order_sn"] == "240101-123"


def test_refund_and_pagination_helpers():
    payload = {"refund_list_get_response": {"refund_list": [{"after_sales_id": 1}]}}
    assert extract_refund_rows(payload)[0]["after_sales_id"] == 1
    assert page_has_more(
        {"response": {"total_count": 51}},
        page=1,
        page_size=50,
        row_count=50,
    )
    assert not page_has_more(
        {"response": {"total_count": 50}},
        page=1,
        page_size=50,
        row_count=50,
    )


def test_pdd_integer_money_is_converted_from_fen():
    assert str(to_decimal(1234, integer_is_cents=True)) == "12.34"
    assert str(to_decimal("12.34", integer_is_cents=True)) == "12.34"
