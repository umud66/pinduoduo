# AGENTS.md

本文件约束所有后续在本仓库工作的编码 Agent。目标是保证项目始终围绕“普通拼多多商家可一键部署的本地 AI 运营诊断工具”演进，而不是逐步变成需要专业运维的服务集群。

## 1. 项目目标

- 本地优先，默认 Windows 小白用户。
- SQLite 默认存储，不要求 PostgreSQL、Redis、Docker。
- 拼多多 API 与报表导入并存。
- SKU 诊断先由程序计算，再让 LLM 解释。
- 支持官方大模型 API 与 OpenAI-Compatible 中转站。
- 图片能力通过 AI Provider 扩展。

任何新技术引入都必须说明它是否会破坏“一键部署”。

## 2. 架构边界

### `app/services/pdd/`

只能在这里处理拼多多 Gateway、签名、接口名、分页、错误码和原始响应。业务层不得到处直接调用 `pdd.*` 接口。

### `app/db/`

平台原始数据要标准化进入本地模型。分析代码不得长期直接依赖拼多多原始 JSON 字段。

### `app/services/diagnosis/`

负责可重复、可测试的确定性诊断。缺失数据必须保持 `None/unknown` 语义，不允许把缺失曝光当 0 曝光，也不允许让 LLM 填补缺失指标。

### `app/services/ai/`

所有模型调用经 Provider/Gateway。禁止在 SKU 业务服务中硬编码某家模型 SDK。

## 3. SQLite 规则

- 默认数据库为 `data/app.db`。
- 保持 WAL、foreign_keys、busy_timeout。
- 写入任务尽量使用短事务和批量写入。
- 建立查询必要的复合索引，尤其是 `shop/date`、`sku/date`。
- 不要因为开发方便而改成要求用户自行安装数据库。
- 公开发布前所有 schema 变化必须走 migration，禁止建议用户删库重建。

## 4. 拼多多 API 规则

- 不假定普通商家应用必然拥有曝光、点击、广告等 scope。
- 新接口加入前先用真实授权店铺做 capability probe。
- 文档写清接口“已真实验证”还是“仅适配待验证”。
- 探针默认只做只读低频调用。
- 涉及订单敏感信息时遵守平台安全要求，日志禁止输出收件人、手机号、地址、Access Token、Client Secret。

## 5. AI 与隐私

- API Key 加密后落库，响应 API 不得返回完整 Key。
- 消费者姓名、电话、地址默认永不发送给 AI Provider。
- Prompt 中要标注哪些值由程序计算，要求模型不要修改或虚构。
- AI 输出用于建议，不作为订单、退款、改价等自动写操作的直接依据。
- 图片生成需要记录来源 SKU、Prompt、Provider、Model，方便复现和审计。

## 6. 诊断规则

每条规则至少包含：

- 稳定的 `code`
- category
- severity
- 样本量门槛
- 当前值
- 基线值
- 触发阈值
- 建议动作
- 单元测试

优先比较“今日/最近期 vs 7 日基线”，后续再增加前 7 日、同商品 SKU、店铺同类等基线。

## 7. 部署规则

最终用户路径必须保持：

```text
下载 -> 双击 exe -> 浏览器打开 -> 配置店铺和 AI -> 使用
```

开发依赖可以复杂，但发布产物不能要求用户安装 Node、Python、数据库或 Docker。若新增原生依赖，必须同步验证 PyInstaller 打包。

## 8. Git 提交规范

**必须按大功能提交，不得按文件提交。**

正确示例：

```text
feat: add PDD connector and capability probe
feat: add AI gateway and image provider support
feat: add deterministic SKU diagnosis engine
```

错误示例：

```text
add models.py
add api.py
update readme
fix typo
```

一个功能涉及模型、API、服务、测试和文档时，应尽量在同一功能 commit 中完整提交。只有确实独立的大功能才能拆分。

每次提交前至少执行：

```text
python -m compileall app scripts tests
pytest
```

如果环境缺依赖导致无法执行，要在提交说明或 PR 中明确记录，不能声称测试通过。

## 9. 测试要求

优先覆盖：

- PDD 签名稳定性
- API 错误解析
- 报表列识别
- SQLite 初始化和关键约束
- 诊断阈值及缺失值行为
- Secret 加解密
- AI Provider 响应解析

外部 API 测试默认使用 MockTransport，不在 CI 中消耗真实店铺或模型额度。

## 10. 当前开发优先级

1. 真实拼多多店铺 capability probe。
2. 商品/SKU/订单/售后的稳定 ETL。
3. 报表映射与 SKU Daily Metric 计算。
4. SKU 诊断 Dashboard。
5. AI 结构化建议。
6. 图片分析与生成工作台。
7. Windows 正式一键发布、自动备份和数据库 migration。

## 11. Release 规则

- Windows 正式发布统一由 `.github/workflows/release.yml` 构建，不手工上传本地产物冒充正式 Release。
- Release 版本使用 `vMAJOR.MINOR.PATCH` Tag；预发布可使用 `vMAJOR.MINOR.PATCH-beta.N`。
- Release Action 必须先跑测试，测试失败不得继续发布。
- 发布资产至少包含 Windows x64 ZIP 与 SHA256 文件。
- PyInstaller 入口必须显式 import 应用对象，避免依赖运行时字符串导入导致打包后缺模块。
- 修改依赖、静态文件目录或启动入口后，应同步检查 `scripts/build_windows.ps1` 和 Release Action。
- Release 自动化相关修改作为一个完整的大功能 commit 提交，不按 workflow、脚本、文档分别拆 commit。

## 12. 产品与技术文档规则

仓库中的产品设计文档是实现约束的一部分，而不是一次性说明材料。

### `docs/product-discussion.md`

记录项目关键技术决策及其原因，包括：

- 为什么采用 SQLite。
- 为什么使用 API + 报表双通道。
- 为什么诊断先规则计算再交给 LLM。
- 为什么采用 Provider/Gateway。
- 为什么以 Windows 一键发布为默认目标。
- 已知风险、待验证能力和明确非目标。

当架构方向或上述关键决策变化时必须同步修改。

### `docs/functional-spec.md`

是功能范围和验收标准的主要来源。新增大功能前，应先检查该功能是否已有定义；如果功能边界、用户流程、数据要求或验收条件发生变化，应在同一大功能 commit 中同步更新该文档。

### 文档状态要求

涉及拼多多 API 时必须明确区分：

```text
verified  = 已使用真实授权店铺验证
adapted   = 代码已适配但尚未真实验证
denied    = 真实授权确认无权限
unknown   = 尚未验证
```

禁止把讨论设想、第三方资料、历史 SDK 中存在的接口直接写成“已实现/已支持”。

### 文档提交粒度

如果文档是某个功能的一部分，应跟随该大功能一起提交；只有像产品基线、架构基线、完整规格说明这种本身就是独立大功能的文档建设，才单独使用 `docs:` commit。

## 13. 前端 UI 模块化规则

前端不得再次退化为单体 `app.js` / `styles.css`。

- `app/static/js/app.js` 只负责应用启动、路由和页面编排，不承载具体业务实现。
- 公共 HTTP、DOM、格式化等基础能力放在 `app/static/js/core/`。
- 可复用交互组件放在 `app/static/js/components/`。
- 每个主页面使用独立的 `app/static/js/pages/<feature>.js`。
- 页面文件包含多个独立工作区或明显增长时，应继续拆成页面子目录/组件，禁止继续向一个文件无限追加。
- 跨页面共享状态集中在 `state.js`，避免散落全局变量。
- CSS 至少按基础、布局、组件、页面拆分；复杂页面可以继续拆专用 CSS。
- 前端生产运行继续使用原生 ES Modules，不得要求普通用户安装 Node/npm 才能启动软件。
- 新增静态目录后必须确认 PyInstaller 仍递归打包整个 `app/static/`。
- UI 架构说明见 `docs/ui-architecture.md`。
