from app.services.importer.report_reader import detect_columns


def test_detects_common_chinese_report_columns() -> None:
    result = detect_columns(["统计日期", "商品ID", "SKU ID", "曝光量", "点击量", "成交金额", "推广消耗"])
    assert result["date"] == "统计日期"
    assert result["goods_id"] == "商品ID"
    assert result["sku_id"] == "SKU ID"
    assert result["impression"] == "曝光量"
    assert result["clicks"] == "点击量"
    assert result["gmv"] == "成交金额"
    assert result["ad_cost"] == "推广消耗"
