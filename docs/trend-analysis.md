# SKU 趋势与同商品对比分析

> 状态：MVP 增强  
> 更新时间：2026-08-18  
> 代码入口：`app/services/trends.py`、`app/services/insights.py`

## 1. 目标

单日诊断回答“今天发生了什么异常”；趋势分析回答：

- 今天相对近期常态是否明显变化。
- 最近 7 日是否比前 7 日持续恶化或改善。
- 最近 30 日走势是什么。
- 同一个商品下，该 SKU 相对其他规格表现如何。
- 当前诊断问题已经连续出现多久。

趋势层不替代确定性诊断规则，也不直接修改 `priority_score`。后续如果要把趋势结果纳入诊断优先级，必须另行修改诊断规则、测试和 `docs/diagnosis-engine.md`。

## 2. 时间窗口

以 SKU 最新有数据日期 `D` 为准，而不是强制使用系统自然日 today。

### 今日 vs 最近 7 日平均

```text
当前期：D
基线期：D-1 ... D-7
```

GMV、销量、订单量等可加总指标使用基线期“日均值”比较。

### 最近 7 日 vs 前 7 日

```text
最近 7 日：D-6 ... D
前 7 日：D-13 ... D-7
```

趋势方向：

```text
change <= -8% -> down
change >= +8% -> up
其他          -> flat
数据不足       -> unknown
```

8% 是趋势展示阈值，不是诊断告警阈值。

## 3. 比率指标聚合

禁止直接平均每天的 CTR/CVR/退款率/ROI。

### CTR

只使用同时存在曝光和点击的日期：

```text
CTR = Σclicks / Σimpression
```

如果没有可用曝光/点击日期：

```text
CTR = unknown
```

### CVR

只使用存在点击数据的日期：

```text
CVR = 对应日期 Σorder_count / Σclicks
```

### 退款率

```text
refund_rate = Σrefund_count / Σorder_count
```

### 推广 ROI

只使用同时存在推广花费与推广 GMV 的日期：

```text
ad_roi = Σad_gmv / Σad_cost
```

缺失值不得按 0 补齐。

## 4. 30 日趋势

SKU 详情最多读取最近 30 个真实指标日，并原样返回实际存在的日期点。

系统不会为了让折线连续而自动补造缺失日期。

趋势图当前主要展示 GMV；接口同时返回销量、订单、退款率、CTR、CVR、ROI，后续可扩展切换指标。

当至少有 14 个指标日时，30 日趋势摘要用“最后 7 个数据日”与“最早 7 个数据日”的日均 GMV 计算变化；不足 14 日时趋势摘要保持 unknown，但仍展示已有点。

## 5. 同商品 SKU 横向比较

比较范围：同一个 `product_id` 下的所有 SKU。

窗口：目标 SKU 最新日期向前 7 日。

每个 SKU 计算：

- 近 7 日 GMV。
- 近 7 日销量。
- 近 7 日订单。
- GMV 排名。
- 商品 GMV 占比。
- 商品销量占比。
- 相对其他 SKU 平均 GMV 的变化。

### SKU 集中度

使用 GMV 占比计算 HHI：

```text
HHI = Σ(gmv_share²)
```

当前展示分档：

```text
HHI >= 0.60       high      高度集中
0.35 <= HHI < .60 medium    较集中
HHI < 0.35        balanced  较均衡
```

HHI 目前只用于描述 SKU 结构，不直接触发诊断规则。

## 6. 异常持续时间

持续时间来源于 `diagnosis_results`，不从趋势数据猜测。

对于当前诊断中每个 issue code，从最新诊断日期向前逐日检查：

```text
当天存在 code -> +1
前一天仍存在 -> +1
日期缺失      -> 停止
code 消失     -> 停止
```

因此：

- 只有真实连续诊断日才算持续。
- 没跑诊断的日期不会自动算作异常仍存在。
- 当前详情显示 `max_consecutive_days` 和每个 issue 的连续天数。

## 7. 店铺趋势概览

API：

```text
GET /api/shops/{shop_id}/trend-overview
```

输出：

- 已跟踪 SKU 数。
- 最近 7 日 GMV 上升数量。
- 下滑数量。
- 持平数量。
- 数据不足数量。
- 下滑最快 SKU 列表。

“下滑最快”只作为导航入口，不等同于最终诊断优先级。SKU 的处理优先级仍由确定性诊断 `priority_score` 决定。

## 8. SKU 趋势详情 API

```text
GET /api/skus/{sku_id}/insights
```

返回：

```text
window_comparison
trend_30d
peer_comparison
persistence
summary
data_quality
```

## 9. Vue UI 模块

```text
frontend/src/components/insights/
├── TrendDelta.vue
├── MetricTrendChart.vue
├── TrendOverview.vue
├── SkuTrendPanel.vue
└── PeerComparison.vue
```

`SkuDiagnosisView.vue` 负责页面编排，不重新实现趋势算法。

`SkuDrawer.vue` 组合：

```text
基础指标
→ 趋势分析
→ 同商品 SKU 对比
→ 确定性诊断
→ AI 建议
```

## 10. 验收要求

- 缺少流量数据时 CTR/CVR 不得伪造为 0。
- 两周数据完整时可得到稳定的近 7 日 vs 前 7 日变化。
- 缺失日期不能被自动补成 0 日。
- 同商品 SKU 排名和份额的分母只能使用同窗口内的真实数据。
- 异常持续时间遇到日期缺口必须停止。
- Vue 页面不得自行复制计算逻辑，所有业务口径由后端返回。
