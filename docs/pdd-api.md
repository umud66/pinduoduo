# 拼多多 API 接入策略

## 核心原则

不要在产品层假定某个商家应用必然拥有全部拼多多开放平台权限。应用类型、审核状态、店铺授权 scope、安全要求都可能影响可调用接口。

因此本项目把拼多多协议细节全部限制在 `app/services/pdd/` 内。

## 当前能力探针

`POST /api/pdd/probe` 会低频测试：

1. `pdd.goods.list.get`
2. `pdd.order.number.list.increment.get`
3. `pdd.refund.list.increment.get`

结果按接口返回：

- `ok`：当前凭据可调用。
- `denied`：疑似权限/scope/授权不足。
- `error`：其他网关、参数、网络或协议错误。

探针不执行修改商品、发货、售后同意等写操作。

## 为什么先探针再同步

同一套软件可能部署到不同商家的电脑上，而每个应用实际权限可能不同。首次配置时先运行探针，系统以后才能做到：

```text
商品接口 OK       -> 开启商品自动同步
订单接口 OK       -> 开启订单自动同步
售后接口 denied   -> 提示申请权限/改用报表补齐
流量无可靠 API    -> 显示报表导入入口
```

## Gateway 与签名

默认 Gateway 配置在 `PDD_AI_PDD_GATEWAY_URL`，当前默认值：

```text
https://gw-api.pinduoduo.com/api/router
```

签名逻辑集中在 `build_sign()`；如果某类新应用改用不同鉴权链路，不要在业务服务中复制签名逻辑，应新增/替换 PDD Adapter。

## 下一步真实店铺验证

拿到可用的 `client_id/client_secret/access_token` 后应保存一份脱敏的能力测试记录，至少确认：

- 返回字段结构
- SKU 标识字段
- 分页/游标方式
- 增量时间窗口限制
- 接口频控
- 错误码
- 是否涉及数据安全能力改造

只有真实授权验证通过的字段，才能进入稳定的 ETL 映射。
