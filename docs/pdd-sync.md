# PDD 数据同步设计

## 状态

当前同步层状态：`adapted`。

这表示代码已经适配以下接口名称和常见响应结构，但尚未使用本项目真实授权店铺逐项验证全部字段：

- `pdd.goods.list.get`
- `pdd.goods.detail.get`
- `pdd.order.list.get`
- `pdd.order.number.list.increment.get`
- `pdd.order.information.get`
- `pdd.refund.list.increment.get`
- `pdd.refund.information.get`

真实可用性仍取决于应用类型、审核状态、店铺授权 scope 和拼多多当前安全要求。

## 同步策略

### 商品 / SKU

首次同步分页读取店铺商品列表，再读取商品详情，将商品和 SKU 标准化写入 SQLite。

### 订单

首次同步使用历史订单列表按天分窗读取，默认回溯 30 天，允许 1~90 天。日常同步使用订单增量接口，按 30 分钟时间窗拆分，再按订单号读取详情。

### 售后

使用售后增量接口按 30 分钟时间窗拆分；如可用则继续读取售后详情。

### SKU 指标

订单和售后写入后，只重算受影响日期的成交/退款指标。曝光、点击、推广等报表字段不会被覆盖。

## 本地任务

同步任务写入 `sync_jobs`，状态包括 `queued`、`running`、`success`、`failed`。同步游标存入 `sync_cursors`，自动同步配置存入 `sync_preferences`。

## 自动同步

不引入 Redis/Celery。桌面进程内使用守护线程定期扫描自动同步配置；到期后提交增量任务到本地线程池。最低自动同步间隔为 15 分钟。

## 安全

同步逻辑只从本地加密存储中解密 Client Secret / Access Token。订单原始 JSON 只保存在本机，不会自动发送给 AI Provider。

如果未来接入收件人解密等敏感接口，必须另行满足拼多多平台的云内/安全要求，并单独做隐私审计。
