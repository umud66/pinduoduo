# 拼多多店铺授权架构

> 状态：`adapted / 待真实店铺验证`
> 更新时间：2026-08-18

## 1. 核心结论

拼多多开放平台应用身份与商家店铺授权必须分开建模：

```text
开放平台应用
Client ID + Client Secret
        ↓
商家进入拼多多授权页并确认
        ↓
回调 code + state
        ↓
pdd.pop.auth.token.create
        ↓
店铺 access_token / refresh_token / owner / scope
        ↓
商品、订单、售后 API
```

普通商家 UI 不允许把“手工填写 Access Token”作为主流程。

## 2. 当前实现

新增：

- `pdd_applications`：开放平台应用身份、回调地址、授权页地址。
- `pdd_shop_authorizations`：某个本地店铺对应的授权账号、Token、scope 与过期信息。
- `pdd_authorization_sessions`：一次授权流程的 `state`、状态与本地过期时间。

应用 Secret、Access Token、Refresh Token 都使用本机 SecretStore 加密。

## 3. 授权 URL

当前代码适配的店铺 WEB 授权页：

```text
https://fuwu.pinduoduo.com/service-market/auth
```

参数：

```text
client_id
response_type=code
redirect_uri
state
```

这组地址/参数来自当前主流拼多多 OpenAPI SDK 的适配实现，但尚未使用本项目自己的真实审核应用和真实授权店铺验证，因此状态为 `adapted`，不能写成 `verified`。

回调地址必须与拼多多开放平台应用详情中登记的地址保持一致。

## 4. Token API

当前适配：

```text
pdd.pop.auth.token.create
pdd.pop.auth.token.refresh
```

Token 字段按实际响应读取：

```text
owner_id
owner_name
access_token
refresh_token
expires_in / expires_at
refresh_token_expires_in / refresh_token_expires_at
scope
```

系统不得硬编码“Access Token 一定 24 小时”或“Refresh Token 一定 30 天”。过期时间优先使用平台响应字段；平台未返回则保持未知。

## 5. 本地回调与公网 Relay

当前实现支持：

```text
http://127.0.0.1:8765/api/pdd/oauth/callback
```

但 **localhost 是否被当前拼多多商家应用类型接受尚未验证**。

因此当前产品必须明确区分：

- `local callback`：开发/真实应用验证用。
- `manual code`：仅开发兜底，不作为普通商家主流程。
- `public relay`：正式本地桌面产品推荐方案，但当前尚未部署。

未来公网 relay 只允许处理中间授权状态/code 交接，不得保存订单、消费者 PII、SKU 经营数据。

## 6. 兼容迁移

现有同步引擎历史上从 `Shop.client_id/client_secret_encrypted/access_token_encrypted` 读取凭证。

本次不直接删除这些字段。新授权成功后，授权服务会临时把当前有效凭证镜像到旧字段，确保现有同步/能力探测不中断。

规则：

- 新授权表是授权语义的真实来源。
- 旧 `Shop` 凭证字段仅是过渡兼容层。
- Vue 普通设置页不再暴露手工 Access Token。
- 后续正式 migration 后再移除兼容镜像；不能直接要求用户删库。

## 7. API

```text
GET  /api/pdd/application
PUT  /api/pdd/application

GET  /api/pdd/shops/{shop_id}/authorization
POST /api/pdd/shops/{shop_id}/authorization/start
POST /api/pdd/authorization/complete
GET  /api/pdd/oauth/callback
POST /api/pdd/shops/{shop_id}/authorization/refresh
DELETE /api/pdd/shops/{shop_id}/authorization
```

原有：

```text
POST /api/pdd/shops/{shop_id}/probe
```

继续用于授权后的 capability probe。

## 8. 安全规则

- `state` 必须随机生成、一次使用并设置本地过期时间。
- code、Token、Secret 不写日志。
- Token 不回显到 Vue。
- “断开本机授权”目前只清除本地凭证，不声称已经在拼多多服务端撤销授权。
- refresh 失败时要求重新授权，不允许自动回退到伪造 Token。
- PDD API 实际权限仍以 capability probe 和真实店铺结果为准。

## 9. 真实验证清单

进入 `verified` 前必须用真实开放平台应用验证：

1. 商家 WEB 授权 URL 是否仍为当前适配地址。
2. 应用类型是否允许 `127.0.0.1` 回调。
3. code 的实际回调参数与错误参数。
4. `pdd.pop.auth.token.create` 返回根节点和字段。
5. refresh 是否对当前商家应用类型有效。
6. Token / refresh Token 的真实生命周期字段。
7. scope 实际返回格式。
8. owner_id 与本地店铺映射。
9. 重新授权、过期、撤销后的错误表现。
10. 商品/订单/售后 API 的真实权限集合。
