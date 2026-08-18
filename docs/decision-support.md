# SKU 运营决策支持规则

> 状态：MVP 增强  
> 更新时间：2026-08-18  
> 代码入口：`app/services/decision_support.py`  
> API：`GET /api/skus/{sku_id}/decision-support`

## 1. 目标与边界

单日确定性诊断回答“当前有哪些异常”；趋势层回答“最近是否持续变化”；决策支持层负责把这些**已经计算出的信号**整理成运营排队依据。

决策支持层不替代诊断引擎，也不修改历史诊断含义。

必须长期保持：

```text
diagnosis.priority_score
= 单次确定性规则诊断优先级

action_priority
= 当前 priority_score + 可解释的趋势上下文加分
```

`action_priority` 只用于“现在先处理哪个 SKU”，不得回写覆盖 `diagnosis_json` 中的 `priority_score`。

## 2. GMV 变化点

变化点用于发现经营水平发生明显阶跃变化的时间。

当前使用无第三方统计库的可解释规则：

- 只读取最近最多 30 个**真实数据日**。
- 每个候选点比较前 3 个真实数据点与后 3 个真实数据点的 GMV 均值。
- 后段均值相对前段均值变化绝对值至少 `20%` 才成为候选。
- 相邻 2 个自然日内的多个候选视为同一变化，保留幅度/置信度更高者。
- 最多返回 3 个候选，并标记最主要变化点。
- 变化点距最新数据日期不超过 7 天时标记 `recent=true`。

缺失日期不会补 0；如果变化点两侧存在明显日历间隔，会降低置信度。

变化点只说明“水平发生变化”，不能单独证明价格、主图、竞品、活动等具体原因。

## 3. 同商品 SKU 份额迁移 / 蚕食候选

比较同一 `product_id` 下所有 SKU 的：

```text
前 7 日窗口：D-13 ... D-7
近 7 日窗口：D-6  ... D
```

只有同时满足以下条件时，才允许标记为候选：

1. 一个 SKU 的 GMV 变化 `<= -20%`。
2. 另一个 SKU 的 GMV 变化 `>= +20%`。
3. 商品整体 GMV 变化位于 `-15% ~ +15%`，即整体经营规模基本稳定。
4. 流出 SKU 和承接 SKU 两个窗口的最小数据覆盖都至少 3 个真实数据日。
5. `min(流出损失, 承接增长) / 流出损失 >= 35%`。

输出包括：

```text
role = loser / winner / neutral
estimated_transfer
transfer_ratio
confidence
product_gmv_change
prior_hhi
recent_hhi
hhi_change
```

这里的“蚕食”只代表**商品内份额迁移候选**，不是因果证明。若商品整体同时大幅下降，不允许把共同下滑误判为 SKU 互相蚕食。

## 4. action_priority

### 4.1 基础分

基础分来自当前诊断问题中最高的：

```text
priority_score
```

如果当前没有可用 `priority_score`：

```text
action_priority = unavailable
```

不允许仅凭趋势数据凭空创建一个诊断优先级。

### 4.2 趋势加分

近 7 日日均 GMV vs 前 7 日：

```text
下降 >= 35%   +12
下降 >= 20%   +8
下降 >= 8%    +4
其他          +0
```

### 4.3 持续时间加分

当前问题最长连续诊断日：

```text
>= 7 天    +10
>= 3 天    +6
>= 2 天    +3
其他       +0
```

持续时间必须来自真实连续 `diagnosis_results.period_end`；日期缺口立即中断。

### 4.4 最近下降变化点

如果主要变化点：

```text
recent = true
且 direction = down
```

则：

```text
下降 >= 40%   +8
下降 >= 20%   +5
```

### 4.5 SKU 结构迁移

如果当前 SKU 被判定为：

```text
role = loser
```

并满足本文第 3 节保守条件：

```text
+6
```

### 4.6 总加分上限

趋势上下文总加分：

```text
boost <= 25
```

最终：

```text
action_priority = min(100, priority_score + boost)
```

分档：

```text
>= 85   urgent / 立即处理
>= 70   high   / 高优先
>= 50   medium / 关注
< 50    normal / 常规
```

API 必须返回每个 adjustment 的 `code / points / reason`，前端必须可以解释“为什么加分”。

## 5. Vue 展示

决策支持组件位于：

```text
frontend/src/components/decision/
├── DecisionSupportPanel.vue
├── ActionPriorityCard.vue
├── ChangePointPanel.vue
└── StructureShiftPanel.vue
```

SKU 详情顺序：

```text
基础指标
→ 运营决策支持
→ 趋势分析
→ 同商品 SKU 对比
→ 确定性诊断
→ AI 建议
```

Vue 不重新计算变化点、迁移比例或 action_priority，只负责展示 API 结果。

## 6. 修改规则

以下任何变化都必须在同一个大功能提交中同步修改代码、测试和本文：

- 变化点前后窗口长度。
- 20% 变化点阈值。
- 商品整体稳定 ±15% 阈值。
- SKU 下跌/增长 ±20% 阈值。
- 35% 迁移覆盖比例。
- action_priority 各加分规则。
- boost 25 分上限。
- action_priority 分档。
- “priority_score 不被回写”的架构边界。

若未来使用更复杂的统计变化点、因果推断或实验数据，必须先更新本文的语义和验收条件，不能直接把相关性输出升级成“已证明因果”。
