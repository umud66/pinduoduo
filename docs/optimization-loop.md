# 优化任务与效果复盘闭环

> 状态：MVP 增强  
> 更新时间：2026-08-18  
> 后端入口：`app/services/optimization.py`、`app/services/optimization_review.py`  
> 数据模型：`app/db/optimization_models.py`  
> Vue 路由：`/tasks`

## 1. 目标

诊断系统不能只停留在“发现问题、给建议”。本模块把确定性诊断中的动作转成可跟踪任务，并在执行后使用同一套本地 SKU 指标做复盘：

```text
诊断问题 / action_priority
        ↓
选择一个具体动作
        ↓
创建优化任务 planned
        ↓
开始执行
        ├─ 冻结执行前 7 日基线
        └─ 创建 3 / 7 / 14 日复盘窗口
        ↓
in_progress
        ↓
记录实际执行内容并标记完成
        ↓
新数据同步 / 导入
        ↓
复盘执行前后指标
        ↓
改善 / 恶化 / 持平或混合 / 数据不足
```

该闭环的目标是形成运营证据，不是自动控制拼多多店铺。

## 2. 数据模型

### `optimization_tasks`

每条任务至少保存：

- `shop_id`、`sku_id`。
- 可选 `diagnosis_id`、`issue_code`、`action_index`。
- `title`。
- `source = diagnosis/manual`。
- `status = planned/in_progress/completed/cancelled`。
- `action_json`：动作、诊断原因、验证指标、执行记录。
- `baseline_json`：开始执行时冻结的执行前指标。
- `started_at`、`completed_at`、`cancelled_at`。

### `optimization_reviews`

每个已开始任务固定生成：

```text
3 天
7 天
14 天
```

每个窗口保存：`due_date`、`status`、`baseline_json`、`observed_json`、`result_json`、`reviewed_at`。

`task_id + window_days` 必须唯一，避免重复生成同一个复盘窗口。

## 3. 状态机

```text
planned
  ↓ start
in_progress
  ↓ complete
completed
```

取消路径：

```text
planned / in_progress
        ↓ cancel
cancelled
```

规则：

- 已取消任务不能重新开始或完成。
- 已完成任务不能取消。
- 如果用户直接“标记完成”但尚未开始，后端先自动执行 start，冻结当时基线，再完成任务。
- 取消任务后，尚未完成的复盘窗口变为 `skipped`。

## 4. 基线口径

任务第一次开始执行的日期记为 `D`。

基线窗口：

```text
D-7 ... D-1
```

不使用执行当天 `D`，因为当天可能同时包含调整前和调整后的数据。

基线只读取真实存在的 `sku_daily_metrics`，缺失日期不补 0。

跨日指标继续遵守 `docs/trend-analysis.md`：

- GMV / 销量 / 订单使用日均值。
- CTR = Σclicks / Σimpression。
- CVR = Σorder_count / Σclicks。
- 退款率 = Σrefund_count / Σorder_count。
- 推广 ROI = Σad_gmv / Σad_cost。

## 5. 复盘窗口

对于 N 天窗口：

```text
D+1 ... D+N
```

只有本地数据最新日期已经覆盖 `D+N`，系统才尝试正式复盘。

为了避免少量数据过度判断，窗口要求至少约 60% 的真实数据日：

```text
required_days = max(2, ceil(N × 60%))
```

当前：

```text
3 天  -> 至少 2 个真实数据日
7 天  -> 至少 5 个真实数据日
14 天 -> 至少 9 个真实数据日
```

如果已经到复盘日期但覆盖不足：`status = insufficient_data`。不得把缺失天数补成 0 后强行判断。

## 6. 验证指标映射

自动复盘只识别有稳定本地数据口径的指标：

- `GMV / 成交额` -> `gmv`
- `销量` -> `sales_qty`
- `订单` -> `order_count`
- `CTR / 点击率` -> `ctr`
- `CVR / 转化率` -> `cvr`
- `退款率` -> `refund_rate`
- `ROI / 投产` -> `ad_roi`

无法稳定计算的验证项，例如“差评率”“退款原因分布”“流量来源占比”，可以继续展示给用户，但当前自动复盘不得伪造这些指标。

如果任务没有任何可识别验证指标，MVP 默认使用 GMV 作为兜底观察项。

## 7. 效果判断

普通指标：

```text
change = (observed - baseline) / baseline
```

退款率是反向指标，下降才表示改善：

```text
effect = -change
```

其他支持指标：`effect = change`。

只对任务所选验证指标中“有基线且可计算”的项目取平均：

```text
effect_score >= +5% -> improved
effect_score <= -5% -> worsened
其他                 -> stable_or_mixed
没有可计算指标         -> insufficient_data
```

基线为 0 时，不计算百分比变化，不使用无穷大或人为常数替代。

## 8. 因果边界

复盘结果必须长期使用“执行前后关联变化”的语言。

禁止仅凭该模块输出：

```text
“因为换了主图，所以 CTR 提升 20%”
```

允许输出：

```text
“执行主图调整后，3 日窗口 CTR 相比执行前基线提升 20%；当前结果仅表示时间上的关联变化。”
```

促销、竞品、自然流量、季节等其他变量可能同时变化，当前 MVP 没有随机实验或严格因果识别能力。

## 9. API

```text
GET  /api/optimization/tasks?shop_id=&status=
GET  /api/optimization/tasks/{task_id}
POST /api/optimization/diagnoses/{diagnosis_id}/tasks
POST /api/optimization/tasks
POST /api/optimization/tasks/{task_id}/start
POST /api/optimization/tasks/{task_id}/complete
POST /api/optimization/tasks/{task_id}/cancel
POST /api/optimization/tasks/{task_id}/reviews/refresh
POST /api/optimization/shops/{shop_id}/reviews/refresh
```

## 10. Vue UI

主路由新增 `/tasks`。

```text
frontend/src/
├── api/optimization.js
├── views/OptimizationTasksView.vue
├── components/optimization/
│   ├── CreateOptimizationTask.vue
│   ├── TaskCard.vue
│   └── ReviewTimeline.vue
└── styles/optimization.css
```

Vue 不计算复盘百分比或效果结论；全部由 Python API 返回。

## 11. 数据库升级说明

本次只新增独立表，没有修改已有表字段。当前 `Base.metadata.create_all()` 可以在已有 SQLite 数据库中创建缺失的新表，因此本次不会要求用户删除数据库。

未来只要修改已有表字段、索引语义或约束，仍必须进入正式 migration 机制，不能把 `create_all()` 当作完整迁移系统。

## 12. 验收要求

- 从诊断问题可以选择一个具体动作创建任务。
- 开始任务时只冻结一次基线，并只生成一组 3/7/14 天窗口。
- 基线不包含执行当天。
- 缺失日期不得补 0。
- 基线为 0 不得伪造百分比提升。
- 退款率下降必须被视为正向改善。
- 复盘数据覆盖不足必须保持 `insufficient_data`。
- 复盘结论不得描述成已证明的因果关系。
- Vue 页面不得复制复盘算法。
