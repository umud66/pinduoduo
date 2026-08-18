# Browser Data Bridge 实验架构

> 分支：`experiment/browser-data-bridge`  
> 状态：`experimental / 未进入正式 Release`  
> 更新时间：2026-08-18

## 1. 目标

当商家暂时无法取得拼多多开放平台开发资质或店铺授权 Token 时，验证一条替代数据接入路线：

```text
用户主动打开受控浏览器
        ↓
用户自行登录拼多多商家后台
        ↓
页面正常产生网络请求/响应
        ↓
Browser Data Bridge 只观察允许域名上的 JSON 响应
        ↓
响应发现层 / 脱敏 / 分类
        ↓
人工确认真实字段与稳定性
        ↓
后续专用 Adapter
        ↓
现有 Product / SKU / Order / Refund / Metric 标准模型
```

本实验不是绕过登录、验证码或平台访问控制，也不是把 Cookie/Token 抽出来伪造私有 API 客户端。

## 2. 为什么使用 Playwright Headed Chromium 做第一阶段验证

第一阶段的目标是验证“用户正常登录 + 持久 Session + 网络响应可观察 + 跨平台可运行”，不是马上做最终嵌入式浏览器。

Playwright Python 提供：

- headed Chromium；
- `launch_persistent_context(user_data_dir)`，可保留浏览器自身 Cookie / localStorage 等登录状态；
- BrowserContext/Page response 事件，可观察页面已经收到的响应；
- Windows/macOS/Linux 支持；
- PyInstaller 打包路径。

代价是 Chromium 浏览器二进制通常会显著扩大最终安装包。因此本分支先验证数据价值和维护成本，不修改正式 Release workflow。

## 3. 安全边界

### 允许

- 用户自己在可见浏览器中登录。
- 浏览器自己发送平台正常请求。
- 程序监听页面收到的 response event。
- 只记录用户明确允许域名的 JSON 响应。
- 对响应做脱敏后保存本机 SQLite，用于接口结构发现。

### 禁止

- 读取或保存密码输入值、验证码。
- 把 Cookie、Authorization、Set-Cookie、Access Token、Refresh Token 写入业务数据库或日志。
- 保存请求头或请求体。
- 导出浏览器 Cookie 后脱离浏览器批量伪造后台请求。
- 绕过登录、风控、人机验证、访问控制。
- 在未建立稳定 Adapter 前把未知私有响应直接写入正式订单/SKU/指标表。
- 自动执行改价、改库存、上下架、退款等店铺写操作。

## 4. 数据存储

新增：

```text
browser_capture_sessions
browser_network_records
```

### `browser_capture_sessions`

保存一次用户主动采集会话：

- `shop_id`
- `status`
- `start_url`
- `allowed_domains`
- `browser_engine`
- `started_at / ended_at`
- `captured_count / skipped_count`
- `error_message`

### `browser_network_records`

只保存发现层数据：

- HTTP method
- 去掉 query value 和 fragment 后的 URL
- query **key 名称**，不保存 query value
- status code
- content type
- resource type
- 候选分类
- 分类 evidence
- 脱敏 JSON body
- body byte size
- 脱敏字段数量
- capture error

不保存 response/request headers。

## 5. 域名边界

默认允许：

```text
pinduoduo.com
yangkeduo.com
```

匹配规则仅允许域本身或真实子域：

```text
mms.pinduoduo.com        allowed
pinduoduo.com            allowed
pinduoduo.com.evil.test  denied
```

实验 UI 允许用户修改 allowlist，但任何新增域都必须是用户明确配置。

## 6. 响应过滤

当前只处理 JSON 类 Content-Type：

```text
application/json
text/json
*+json
```

单条响应默认最大：

```text
512 KiB
```

超过上限只记录跳过，不把大响应塞进 SQLite。

## 7. 脱敏

发现层会递归屏蔽常见敏感字段，包括：

```text
password / passwd
access_token / refresh_token
authorization / cookie / session
mobile / phone
receiver_name / receiver_phone
address / consignee
id_card
```

普通字符串中识别到手机号或 email 时也会做遮盖。

该脱敏只能降低风险，不能替代真实商家数据审计。真实响应结构确认后，应优先建立“白名单字段 Adapter”，逐步减少通用 body 保存范围。

## 8. 候选分类

发现层当前只根据 URL 和有限 JSON key 做启发式分类：

```text
goods
orders
refunds
traffic
promotion
unknown
```

该分类仅用于帮助开发者寻找有价值的响应，**不是正式业务字段映射**。

## 9. Adapter 晋级流程

一个浏览器响应只有满足以下流程后才能进入正式标准模型：

```text
unknown / candidate
        ↓
真实商家页面重复观察
        ↓
确认 URL/响应结构至少在多次会话稳定
        ↓
明确字段含义、金额单位、时间单位、分页方式
        ↓
建立专用 Adapter + fixture
        ↓
单元测试
        ↓
真实店铺回归验证
        ↓
adapted / verified
        ↓
才允许写入标准模型
```

每个 Adapter 至少记录：

- 页面入口；
- 响应识别条件；
- 稳定字段；
- 数据口径；
- 缺失值规则；
- PII 字段；
- 真实验证日期；
- 当前状态。

## 10. Browser Profile

每个本地店铺使用独立目录：

```text
<data_dir>/browser/shop-<id>/profile
<data_dir>/browser/shop-<id>/downloads
```

登录 Session 由 Chromium 自己管理。应用代码不读取 profile 中的 Cookie 数据。

用户清除这个 profile 后需要重新登录。

## 11. 后端 API

```text
GET  /api/browser-bridge/status
POST /api/browser-bridge/sessions
POST /api/browser-bridge/sessions/stop
GET  /api/browser-bridge/shops/{shop_id}/sessions
GET  /api/browser-bridge/sessions/{session_id}
GET  /api/browser-bridge/sessions/{session_id}/records
```

`records` 默认不返回完整 body；当前 Vue 只展示 URL、分类、大小、脱敏数量和结构证据。

## 12. Vue UI

数据中心新增：

```text
components/data/BrowserDataBridge.vue
api/browser-bridge.js
styles/browser-bridge.css
```

主要流程：

```text
填写实际商家后台 URL
→ 打开可见 Chromium
→ 用户自行登录/浏览
→ 页面实时显示已捕获响应摘要
→ 选择历史采集会话
```

## 13. 开发安装

Browser Data Bridge 是可选依赖：

```bash
pip install -e ".[dev,browser]"
playwright install chromium
```

没有安装 Playwright 时，FastAPI/Vue/原 OpenAPI/报表功能仍应正常启动，Browser Data Bridge 只显示“组件未安装”。

## 14. 当前明确不做

第一版不做：

- Chromium 嵌入 Vue 窗口内部；
- headless 后台爬取；
- Cookie 导出；
- 私有 API 重放器；
- 自动登录；
- 自动绕验证码；
- 网络响应自动写入标准业务表；
- 正式 Release 打包 Chromium。

## 15. 合并主线的最低条件

该实验分支不得仅因“代码能运行”就合入主线。至少需要真实商家验证：

1. 常用登录方式可以在 persistent profile 中正常使用。
2. 不出现明显账号风控异常。
3. 至少找到 2~3 类有稳定业务价值的响应或官方报表下载流程。
4. 找到的响应结构在多次会话中具有可维护稳定性。
5. Buyer PII 能够明确识别并从标准化链路排除。
6. 至少完成一个正式 Adapter 和对应 fixture/test。
7. 评估 Chromium 安装包体积与 Windows/macOS/Linux 发布成本。
8. 明确平台规则/服务协议风险并决定产品是否允许默认启用。

满足后再讨论是否合入 `master`，以及最终采用独立浏览器窗口、插件或嵌入式浏览器。
