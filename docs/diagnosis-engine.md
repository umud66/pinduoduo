# SKU 诊断引擎设计

## 状态

当前诊断引擎状态：`MVP / 持续增强`。

诊断原则：

- 指标计算和异常判断由程序完成。
- 大模型只负责解释、补充动作和生成运营建议。
- 缺失数据保持 Unknown，不把缺失值当 0。
- 小样本必须通过最低样本门槛，避免百分比误报。
- 诊断输出必须包含证据、优先级、置信度和验证方式。

## 诊断链路

```text
SKU Daily Metric
      ↓
当前期 vs 最近 7 日基线
      ↓
数据覆盖检查
      ↓
GMV 变化拆解
      ↓
确定性规则诊断
      ↓
影响度 + 置信度 + 优先级
      ↓
按优先级排序
      ↓
规则动作 + 验证指标
      ↓
可选 AI 跟进
```

## GMV 拆解

当曝光、点击、订单和 GMV 数据完整时，使用：

```text
GMV ≈ 曝光 × CTR × CVR × 客单价
```

系统比较当前期和基线期的四个因素，把 GMV 缺口按各因素恶化程度进行诊断性分摊。

输出示例：

```json
{
  "mode": "full_funnel",
  "estimated_gmv_loss": 320.50,
  "factors": [
    {
      "code": "click",
      "label": "点击率",
      "change": -0.31,
      "loss_share": 0.52,
      "estimated_loss": 166.66
    }
  ]
}
```

该金额用于运营排序，不是财务会计意义上的严格因果归因。

如果缺少曝光/点击数据，但订单和 GMV 可用，则自动降级为：

```text
GMV ≈ 订单量 × 客单价
```

如果连上述数据也不足，则不强行拆解。

## 问题结构

每个诊断问题至少包含：

```text
code
category
severity
title
reason
evidence
actions
validation_metrics
impact_score
confidence
priority_score
estimated_loss
```

### impact_score

范围 0~100，表示该问题对经营结果的潜在影响程度。

### confidence

范围 0~1，综合：

- 当前样本量。
- 基线天数。
- 所需指标是否完整。

### priority_score

用于决定运营处理顺序：

```text
priority_score =
    impact_score × 68%
  + confidence × 100 × 32%
```

具体权重后续可根据真实店铺反馈调整。

## 当前规则

当前已实现：

- `TRAFFIC_DROP`：曝光明显下降。
- `CTR_DROP`：点击率下降。
- `CVR_DROP`：支付转化率下降。
- `AOV_DROP`：客单价下降。
- `PRICE_CHANGE_SALES_DROP`：价格明显变化并伴随销量下降。
- `SALES_DROP`：销量结果指标明显下降。
- `REFUND_HIGH`：退款率异常。
- `STOCK_RISK`：可售库存过低。
- `STOCK_EXCESS`：库存周转过慢。
- `AD_ROI_LOW`：推广 ROI 偏低。

`SALES_DROP` 是结果类问题。如果系统已经识别出更具体的流量、点击、转化等根因，它的优先级应低于根因问题。

## 数据质量

诊断结果包含：

```text
coverage_score
baseline_days
baseline_score
overall_score
confidence
available
missing
```

前端必须向用户明确显示数据完整度。

数据不足时应告诉用户需要补充什么数据，而不是给出过度确定的结论。

## 健康分

健康分范围：

```text
0 ~ 100
```

健康分由问题优先级递减扣分生成。

多个问题同时出现时采用递减权重，避免简单累加导致一个 SKU 因多个高度相关问题直接被扣到 0。

## AI 约束

AI Prompt 必须告诉模型：

- 当前指标由程序计算。
- 不允许改写数值。
- 不允许补造缺失指标。
- 相关性不能描述成确定因果。
- 优先处理 `priority_score` 最高的问题。
- 每条建议必须给出验证指标和观察周期。
- 数据置信度低时优先建议补数据。

## UI 展示

SKU 详情应显示：

1. 健康分与严重度。
2. 经营结论。
3. 数据覆盖度和基线天数。
4. 估算 GMV 缺口。
5. GMV 因素拆解。
6. 按优先级排序的问题。
7. 每个问题的影响度、置信度和触发依据。
8. 可执行动作。
9. 验证指标。
10. AI 补充建议。

## 后续增强

后续优先增加：

- 最近 7 日 vs 前 7 日。
- 30 日趋势和变化点检测。
- 同商品 SKU 横向比较。
- SKU 之间的流量/销量蚕食。
- 类目和店铺基线。
- 低销量 SKU 的贝叶斯收缩。
- 中位数/MAD 异常检测。
- 诊断持续时间。
- 优化任务与实验反馈闭环。
