# PDD 数据同步设计

## 状态

当前同步层状态：`adapted`。商品、订单、售后接口名称和常见响应结构尚未使用本项目真实审核应用 + 真实授权店铺逐项验证。

当前适配：

- `pdd.goods.list.get`
- `pdd.goods.detail.get`
- `pdd.order.list.get`
- `pdd.order.number.list.increment.get`
- `pdd.order.information.get`
- `pdd.refund.list.increment.get`
- `pdd.refund.information.get`

真实可用性仍取决于应用类型、审核状态、店铺授权 scope 和拼多多当前安全要求。

## 授权前置条件

同步不再把“填写 Client ID/Secret/Access Token”当正式商家入口。

正式链路：

```text
配置开放平台应用
→ 商家店铺授权
→ Token create / refresh
→ capability probe
→ 同步商品 / 订单 / 售后
```

授权详细规则见 `docs/pdd-authorization.md`。

当前新授权成功后会把有效凭证临时镜像到旧 `Shop` 凭证字段，以保持现有同步服务兼容。新授权表是语义真实来源，镜像只是过渡实现。

如果平台返回 Token 过期字段，独立 Token 生命周期调度器会在到期前尝试 refresh；refresh 已过期/失败则要求重新授权。平台未返回过期字段时不猜刷新周期。

## 同步策略

### 商品 / SKU

首次同步分页读取店铺商品列表，再读取商品详情，将商品和 SKU 标准化写入 SQLite。商品同步完成后尝试把过去未能匹配 SKU 的订单明细和售后记录重新关联到新同步 SKU，并刷新最新价格与库存维度。

### 订单

首次同步使用历史订单列表按天分窗，默认回溯 30 天，允许 1~90 天。日常同步使用订单增量接口按 30 分钟时间窗拆分，再按订单号读取详情。

只有新的详情确实包含商品明细列表时才替换本地 `order_items`；不完整响应不能删除已有明细。

### 售后

使用售后增量接口按 30 分钟时间窗拆分；如可用继续读取售后详情。更新记录时把旧日期和新日期都加入重算范围。

### SKU 指标

订单和售后写入后只重算受影响日期的成交/退款指标。重算前清零这些日期已有成交字段，再根据本地订单和售后重新聚合。曝光、点击、访客、推广等报表字段不会被成交重算覆盖。

## 失败恢复与幂等

同步任务写入 `sync_jobs`，状态包括 `queued/running/success/failed`，保存原始同步参数，失败后可按原参数重试。

应用启动时会把残留在 `queued/running` 的任务标记为 `failed + recoverable`。商品、订单、售后按平台 ID upsert；游标只在资源完整成功后推进。

## 请求级重试

PDD Client 对 HTTP 429、5xx、网络异常和明确的系统繁忙/频率过高等临时错误有限重试。权限不足、参数错误等确定性错误不自动重试。

## 自动诊断

完整同步、订单、售后或增量同步确实产生经营数据变化后，会自动重新运行店铺 SKU 的确定性诊断。相同 `SKU + period_end` 采用更新语义；确定性诊断变化时旧 AI 分析清空。

## 本地任务与自动同步

不引入 Redis/Celery。桌面进程线程池执行同步任务，守护线程扫描自动同步配置；最低自动同步间隔 15 分钟。

授权 Token 生命周期由独立 `pdd-token-refresh` 守护线程维护，避免把 OAuth 职责耦合进同步 Runner。

## UI 状态

顶部显示当前店铺同步状态。数据中心展示当前任务、进度、历史和错误。授权状态/开放平台应用配置统一在设置页的拼多多授权组件中维护。

## 安全

同步只从本地加密存储解密 Secret / Token。订单原始 JSON 只保存在本机，不自动发送 AI Provider。日志禁止输出授权 code、Token、Secret、收件人、手机号和地址。
