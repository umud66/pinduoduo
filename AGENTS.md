# AGENTS.md

本文件约束所有后续在本仓库工作的编码 Agent。项目目标是“普通拼多多商家可一键部署的本地 AI 运营诊断与优化闭环工具”。

## 1. 产品与部署目标

- 本地优先，面向非技术商家。
- 正式发布支持 Windows、macOS、Linux。
- SQLite 默认存储，不要求 PostgreSQL、Redis、Docker。
- 数据接入优先级：官方 OpenAPI > 官方商家报表 > 经验证的 Browser Data Bridge Adapter。
- SKU 诊断由程序确定性计算，LLM 负责解释和补充建议。
- 优化动作必须由用户明确选择/执行，AI 不得直接写店铺状态。
- 正式用户路径保持：`下载 -> 解压/打开应用 -> 浏览器打开 -> 配置 -> 使用`。
- 开发环境允许 Python/Node.js；正式发布包不得要求最终用户安装它们。

## 2. 后端架构边界

- `app/services/pdd/`：拼多多授权协议、Token 生命周期、Gateway、签名、接口、分页、错误和 OpenAPI 原始响应。
- `app/db/pdd_auth_models.py`：开放平台应用、店铺授权、授权 state 会话。
- `app/services/browser_bridge/`：实验性浏览器会话、网络 response 过滤、脱敏、候选分类；不得包含正式业务字段猜测。
- `app/db/browser_models.py`：Browser Data Bridge 采集会话和发现层响应记录。
- `app/db/`：平台数据标准化、本地任务/复盘模型；标准化本地模型是分析主来源。
- `app/services/diagnosis/`：确定性单日诊断，缺失数据保持 `None/unknown`。
- `app/services/trends.py`：纯趋势/窗口/同商品比较算法，不访问数据库。
- `app/services/insights.py`：组织趋势、同商品 SKU、持续时间等经营洞察。
- `app/services/decision_support.py`：变化点、结构迁移和 `action_priority`。
- `app/services/optimization.py`：优化任务生命周期、基线冻结和复盘数据组织。
- `app/services/optimization_review.py`：纯复盘指标映射和效果比较算法。
- `app/services/ai/`：所有模型调用经 Provider/Gateway。

业务公式和私有响应字段映射不得复制到 API 层或 Vue 层。

## 3. SQLite 与运行数据规则

- 数据目录由 `app/core/paths.py` 按运行环境解析。
- 源码开发默认 `data/`。
- Windows 冻结版保持 `<exe>/data/`。
- macOS 冻结版默认 `~/Library/Application Support/PDD AI Operator/`。
- Linux 冻结版默认 `$XDG_DATA_HOME/pdd-ai-operator/`，无 XDG 时使用 `~/.local/share/pdd-ai-operator/`。
- `PDD_AI_DATA_DIR` 可以显式覆盖。
- 数据库和 `secret.key` 必须一起备份。
- 保持 WAL、foreign_keys、busy_timeout。
- 仅新增独立表时，当前 `create_all()` 可创建缺失表；修改已有表字段/约束/索引语义时必须进入版本化 migration，不能要求用户删库。
- Browser profile 位于 `<data_dir>/browser/shop-<id>/profile`，应用代码不得读取其中 Cookie 作为业务凭证。

## 4. 拼多多应用与店铺授权规则

接口/能力状态必须区分：

```text
verified  = 真实审核应用 + 真实授权店铺验证
adapted   = 代码已适配但未真实验证
denied    = 已确认无权限
unknown   = 未验证
```

授权语义必须长期保持：

```text
Client ID + Client Secret = 开放平台应用身份
商家官方授权页确认        = 店铺对应用授权
access_token / refresh_token = 授权结果
capability probe          = 授权完成后验证实际 API 权限
```

硬性规则：

- 普通商家 UI 不允许把“手工填写 Access Token”作为正式主流程。
- `client_id/client_secret` 不等于店铺授权。
- state 随机、一次使用并有本地过期时间。
- code、Token、Client Secret 禁止写日志或回显前端。
- Token 生命周期只能读取平台响应字段，不硬编码未经验证的有效期。
- refresh 失败或 refresh_token 过期时必须重新授权。
- “断开本机授权”不得声称已经在平台服务端撤销。
- 当前授权 endpoint 进入 `verified` 前必须用本项目真实审核应用和真实店铺验证。
- localhost callback 未验证前不能承诺可用于正式产品。
- 详细口径见 `docs/pdd-authorization.md`。

现有 `Shop.client_id/client_secret_encrypted/access_token_encrypted` 是过渡兼容字段；新授权表是授权语义真实来源。

## 5. Browser Data Bridge 实验规则

详细规则见 `docs/browser-data-bridge.md`。该能力当前只允许在 `experiment/browser-data-bridge` 等明确实验分支开发，未满足合并条件前不得当作正式数据通道宣传。

### 5.1 定位

Browser Data Bridge 是用户主动触发的**只读响应观察器**：

```text
用户可见浏览器
→ 用户自行登录
→ 页面正常请求
→ 观察 response
→ 域名过滤 / 脱敏 / 分类
→ discovery records
→ 专用 Adapter
→ 标准模型
```

禁止把它实现成后台隐形爬虫或绕过登录的私有 API 客户端。

### 5.2 登录与认证硬性边界

- 不读取/保存用户名、密码、验证码输入值。
- 不保存请求 headers、Cookie、Set-Cookie、Authorization 或请求 body。
- 不允许导出 Cookie/Token 后脱离浏览器重放私有接口。
- 不绕过验证码、人机验证、账号风控或访问控制。
- 用户必须看到浏览器窗口并自行完成登录/验证。
- 浏览器登录 Session 由浏览器 persistent profile 自己维护。

### 5.3 响应采集硬性边界

- 只采集 allowlist 域名本身或真实子域。
- 默认只采集 JSON Content-Type。
- URL 入库前必须删除 query values 和 fragment；只可保留 query key 名称。
- 单条 body 必须有大小上限；当前默认 512 KiB。
- response body 入库前必须递归脱敏 Token/Cookie/手机号/地址/收件人等敏感字段。
- Vue 默认只显示响应摘要，不主动读取完整 body。
- 通用脱敏只是 discovery 阶段保护；正式 Adapter 应转向白名单字段提取。

### 5.4 标准模型写入边界

**未知私有响应不得直接写入 `products/skus/orders/refunds/sku_daily_metrics`。**

必须经过：

```text
真实页面重复观察
→ 稳定结构确认
→ 字段/单位/分页/PII 文档
→ 专用 Adapter
→ fixture + 单元测试
→ 真实店铺回归
→ adapted / verified
→ 才允许标准化写入
```

Adapter 规则变化必须同步更新专题文档和测试。

### 5.5 浏览器技术边界

- 第一阶段使用 Playwright headed Chromium 只为验证可行性，不代表最终 UI 必须使用 Playwright。
- Playwright 必须作为可选依赖；未安装时主应用仍能正常启动。
- Playwright 实例必须在其所属线程内创建/使用，避免跨线程共享。
- Chromium 尚未加入正式 Release；未完成体积和多平台评估前不得修改发布声明为“已支持浏览器版”。

## 6. AI 与隐私

- API Key 加密落库。
- 消费者姓名、电话、地址默认不发送 AI。
- AI 输出不得直接驱动订单、退款、改价、上下架、库存等写操作。
- AI 只能解释系统已有数据、提出候选动作；用户必须明确确认并自行执行店铺变更。
- Browser discovery response 不得未经白名单清洗直接发送 AI。

## 7. 诊断、趋势与决策规则

每条诊断规则至少定义稳定 code、category、severity、样本门槛、当前/基线/变化、impact_score、confidence、priority_score、actions、validation_metrics 和单元测试。

修改诊断阈值、基线算法、健康分、GMV 拆解或优先级公式时，必须同步更新 `docs/diagnosis-engine.md` 和必要的 `docs/functional-spec.md`。

趋势分析必须遵守：时间窗口以 SKU 最新真实数据日为锚点；CTR/CVR/退款率/ROI 跨日重新聚合分子/分母；缺失数据保持 unknown；30 日图不补造日期；同商品排名使用同窗口真实数据；异常持续时间遇到日期缺口必须中断。修改这些口径时同步更新 `docs/trend-analysis.md` 和测试。

决策支持必须遵守：

- `priority_score` 保持单次确定性诊断语义。
- `action_priority` 只能叠加可解释上下文，不得覆盖历史诊断分数。
- 变化点和 SKU 份额迁移只能描述为经营证据/候选，不得描述成确定因果。
- 修改规则时同步更新 `docs/decision-support.md` 和测试。

## 8. 优化任务与复盘规则

优化闭环以 `docs/optimization-loop.md` 为详细口径：

```text
诊断动作
→ planned
→ start 冻结执行前 7 日基线
→ in_progress
→ complete
→ 3/7/14 日复盘
```

- 基线为 `D-7 ... D-1`。
- 复盘为 `D+1 ... D+N`，N 当前固定 3/7/14。
- 缺失日期不补 0。
- 数据覆盖不足保持 `insufficient_data`。
- 基线为 0 不伪造百分比提升。
- 退款率是反向指标。
- 复盘只描述执行前后关联变化，不声称证明因果。
- Vue 不得计算 `effect_score/outcome`。

## 9. Git 提交规范

**必须按大功能提交，不按文件提交。** 一个功能涉及源码、测试、API、数据库、Vue、构建脚本和文档时，应按业务边界形成少量完整 commit，禁止机械文件提交。

实验分支也必须遵守该规则。

## 10. 测试规则

后端至少运行 `python -m compileall app scripts tests` 与 `pytest`；前端至少运行 `npm install/npm ci` 与 `npm run build`。无法执行必须明确记录环境限制，不得声称通过。

算法/协议纯逻辑优先写纯函数测试。

Browser Data Bridge 至少覆盖：

- 域名 allowlist 与伪子域拒绝；
- URL query value 删除；
- Token/Cookie/PII 脱敏；
- body 大小上限；
- JSON 类型过滤；
- 候选分类 unknown fallback；
- 正式 Adapter 后必须增加对应 fixture/parser 测试。

涉及 Release/平台的改动必须通过原生 GitHub Runner 验证。

## 11. Release 规则

- 正式 Release 统一由 `.github/workflows/release.yml` 构建。
- 当前稳定矩阵：Windows x64、Linux x64、macOS arm64、macOS Intel x64。
- Release 必须先运行 Python 测试与 Vue build，再执行平台矩阵。
- 当前正式 Release **不包含 Browser Data Bridge Chromium**。
- Browser Data Bridge 进入正式 Release 前必须评估 Chromium 二进制体积、PyInstaller 资源路径、平台依赖和升级策略，并同步更新 `docs/release.md`、`docs/platform-support.md`。
- macOS Developer ID 签名/notarization 未配置前，禁止声称已签名。

## 12. 文档是实现的一部分

以下改动必须在同一大功能 commit 中形成或更新文档：架构/技术栈、模块边界、数据结构/字段口径、PDD 授权/API、Browser Data Bridge、安全边界、诊断/趋势/决策/复盘、UI 主流程、发布部署、Git/测试规则。

文档入口：

- Browser 实验：`docs/browser-data-bridge.md`。
- PDD 店铺授权：`docs/pdd-authorization.md`。
- PDD 同步：`docs/pdd-sync.md`。
- UI：`docs/ui-architecture.md`。
- 诊断：`docs/diagnosis-engine.md`。
- 趋势：`docs/trend-analysis.md`。
- 决策支持：`docs/decision-support.md`。
- 优化闭环：`docs/optimization-loop.md`。
- 发布：`docs/release.md`、`docs/platform-support.md`。

如果代码与文档冲突，提交不得视为完整。

## 13. Vue 前端强制架构

前端统一使用 Vue 3 + Vite + Vue Router + Pinia：

```text
frontend/src/
├── api/
├── components/
│   ├── data/
│   ├── diagnosis/
│   ├── insights/
│   ├── decision/
│   ├── optimization/
│   └── settings/
├── layouts/
├── router/
├── stores/
├── styles/
└── views/
```

- `index.html` 只能作为 Vite 挂载入口。
- 新主页面建立独立 `*View.vue` 和路由。
- View 只做页面编排；多个独立工作区拆到 `components/<domain>/`。
- Browser UI 放 `components/data/BrowserDataBridge.vue`，Playwright 逻辑只在 Python。
- API URL 和通用请求错误处理集中到 `src/api/`。
- Pinia 只保存真正跨页面共享状态。
- 不允许重新退化为单个超大 `.vue` / `.js` / CSS 文件。
- 复杂新样式使用独立领域 CSS。
- `app/static/` 是 Vite 生成产物，不作为源码手工维护。
- UI 架构变化必须同步更新 `docs/ui-architecture.md`。

## 14. 当前实验分支优先级

`experiment/browser-data-bridge` 优先验证：

1. 用户真实商家后台登录能否稳定保持在 persistent profile。
2. 典型经营页面能否发现稳定 JSON response。
3. 商品/订单/售后/流量/推广中哪些数据值得建立 Adapter。
4. Buyer PII 和账号安全风险是否可以稳定隔离。
5. 至少完成一个真实 Adapter + fixture/test。
6. 评估浏览器方案的账号风控、维护成本和平台规则风险。
7. 再决定最终形态：独立 Chromium、浏览器插件、嵌入式浏览器或只做报表辅助。

主线 OpenAPI/报表/诊断功能不得因为该实验分支而退化。
