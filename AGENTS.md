# AGENTS.md

本文件约束所有后续在本仓库工作的编码 Agent。项目目标是“普通拼多多商家可一键部署的本地 AI 运营诊断工具”。

## 1. 产品与部署目标

- 本地优先，面向非技术商家。
- 正式发布支持 Windows、macOS、Linux。
- SQLite 默认存储，不要求 PostgreSQL、Redis、Docker。
- 拼多多 API 与报表导入并存。
- SKU 诊断由程序确定性计算，LLM 负责解释和补充建议。
- 支持 OpenAI-Compatible 中转站以及其他 Provider。
- 正式用户路径必须保持：`下载 -> 解压/打开应用 -> 浏览器打开 -> 配置 -> 使用`。
- 开发环境允许 Python/Node.js，但正式发布包不得要求最终用户安装它们。

## 2. 后端架构边界

- `app/services/pdd/`：拼多多 Gateway、签名、接口、分页、错误和原始响应。
- `app/db/`：平台数据标准化，本地模型是分析主来源。
- `app/services/diagnosis/`：确定性单日诊断，缺失数据保持 `None/unknown`。
- `app/services/trends.py`：纯趋势/窗口/同商品比较算法，不访问数据库。
- `app/services/insights.py`：从数据库组织趋势、同商品 SKU、持续时间等经营洞察。
- `app/services/ai/`：所有模型调用经 Provider/Gateway。

## 3. SQLite 与运行数据规则

- 数据目录由 `app/core/paths.py` 按运行环境解析。
- 源码开发默认 `data/`。
- Windows 冻结版保持 `<exe>/data/` 便携目录。
- macOS 冻结版默认 `~/Library/Application Support/PDD AI Operator/`。
- Linux 冻结版默认 `$XDG_DATA_HOME/pdd-ai-operator/`，无 XDG 时使用 `~/.local/share/pdd-ai-operator/`。
- `PDD_AI_DATA_DIR` 可以显式覆盖。
- 数据库和 `secret.key` 必须一起备份。
- 保持 WAL、foreign_keys、busy_timeout。
- schema 变化在正式发布前必须 migration，不能要求用户删库重建。

## 4. 拼多多 API 规则

接口状态必须区分：

```text
verified  = 真实授权店铺验证
adapted   = 代码已适配但未真实验证
denied    = 已确认无权限
unknown   = 未验证
```

不假定曝光、点击、推广 scope；新接口先 capability probe；日志禁止输出收件人、手机号、地址、Token、Secret。

## 5. AI 与隐私

API Key 加密落库；消费者姓名、电话、地址默认不发送 AI；AI 输出不得直接驱动订单、退款、改价等写操作。

## 6. 诊断与趋势规则

每条诊断规则至少定义稳定 code、category、severity、样本门槛、当前/基线/变化、impact_score、confidence、priority_score、actions、validation_metrics 和单元测试。

修改诊断阈值、基线算法、健康分、GMV 拆解或优先级公式时，必须同步更新 `docs/diagnosis-engine.md` 和必要的 `docs/functional-spec.md`。

趋势分析必须遵守：

- 时间窗口以 SKU 最新真实数据日为锚点。
- 今日 vs 7 日均值与最近 7 日 vs 前 7 日的口径以 `docs/trend-analysis.md` 为准。
- CTR/CVR/退款率/ROI 跨日不得简单平均每日百分比，要重新聚合分子/分母。
- 缺失流量/推广数据保持 unknown，不允许补 0。
- 30 日图只展示真实存在的数据日，不自动补造日期。
- 同商品 SKU 排名只能使用同一窗口内的真实数据。
- 异常持续时间只认连续的真实诊断日期，日期缺口必须中断。
- 趋势方向、同商品排名、HHI 当前只用于洞察，不得未经规则变更直接改写 `severity / health_score / priority_score`。

修改上述趋势窗口、8% 展示阈值、HHI 分档、持续时间算法或趋势与诊断融合方式时，必须同步更新 `docs/trend-analysis.md`、相关测试，并在需要时更新 `docs/diagnosis-engine.md`。

## 7. Git 提交规范

**必须按大功能提交，不按文件提交。** 一个功能涉及源码、测试、CI、构建脚本和文档时，应在同一功能 commit 中完整提交。

## 8. 测试规则

后端至少运行：`python -m compileall app scripts tests` 与 `pytest`。前端至少运行：`npm install/npm ci` 与 `npm run build`。无法执行必须明确记录环境限制，不得声称通过。

趋势/统计算法必须优先写纯函数测试，至少覆盖：缺失值、窗口边界、比率聚合、同商品排名和连续日期逻辑。

涉及 Release/平台的改动必须通过原生 GitHub Runner 验证对应 PyInstaller 构建。不能用一个平台的本地构建结果声称另一个平台已经可发布。

## 9. Release 规则

- 正式 Release 统一由 `.github/workflows/release.yml` 构建。
- 当前稳定矩阵：Windows x64、Linux x64、macOS arm64、macOS Intel x64。
- Runner 应使用明确的平台/架构标签；修改 Runner 时先核对 GitHub 官方当前支持状态。
- Release 必须先运行 Python 测试与 Vue build，再执行平台矩阵。
- Windows 使用 `scripts/build_windows.ps1`。
- Linux/macOS 使用 `scripts/build_unix.sh`。
- 每个平台必须产生独立 SHA256，最终 Release 还必须包含 `SHA256SUMS.txt`。
- 矩阵 job 只构建并上传临时 artifact；只能由单独 `publish` job 创建/更新 GitHub Release，避免并发竞态。
- 正式稳定版不得在某个平台失败后静默发布缺少该平台资产的不完整 Release。
- macOS Developer ID 签名/notarization 未配置前，文档必须明确标记，禁止声称已签名。
- 修改 Vite 输出、静态目录、数据目录、PyInstaller、Node/Python 版本、平台或架构时必须同步检查 Release Action 和平台文档。

## 10. 文档是实现的一部分

以下改动**必须在同一大功能 commit 中形成或更新文档**：

- 架构或技术栈改变。
- 目录职责和模块边界改变。
- 数据结构、数据来源、字段口径改变。
- 拼多多 API 能力状态改变。
- 诊断阈值、算法、基线、评分和优先级改变。
- 趋势窗口、比率聚合、同商品比较、持续时间等运营分析口径改变。
- UI 主流程、用户操作方式改变。
- 发布平台、CPU 架构、部署、依赖、构建流程改变。
- 安全与隐私规则改变。
- Git/测试/Agent 工程规则改变。

关键决策写 `docs/product-discussion.md` 或独立 decision/migration 文档；功能验收写 `docs/functional-spec.md`；前端架构写 `docs/ui-architecture.md`；诊断写 `docs/diagnosis-engine.md`；趋势分析写 `docs/trend-analysis.md`；同步写 `docs/pdd-sync.md`；发布写 `docs/release.md` 和 `docs/platform-support.md`。如果代码与文档冲突，提交不得视为完整。

## 11. Vue 前端强制架构

前端源码位于 `frontend/`，统一使用 Vue 3 + Vite + Vue Router + Pinia。

```text
frontend/src/
├── api/         HTTP 接口封装
├── components/  可复用领域组件
├── layouts/     页面骨架
├── router/      路由
├── stores/      跨页面状态
├── styles/      全局样式
└── views/       路由页面
```

- `index.html` 只能作为 Vite 挂载入口，禁止放业务实现。
- 新主页面建立独立 `*View.vue` 和路由。
- View 只做页面编排；多个独立工作区拆到 `components/<domain>/`。
- 趋势类组件统一放在 `components/insights/`，禁止在 `SkuDiagnosisView.vue` 或 `SkuDrawer.vue` 重复实现分析算法。
- API URL 和通用请求错误处理集中到 `src/api/`。
- Pinia 只保存跨页面共享状态。
- 不允许重新退化为单个超大 `.vue` / `.js` / CSS 文件。
- 复杂新样式使用独立 CSS（例如 `styles/trends.css`），不要继续无限增长 `app.css`。
- `app/static/` 是 Vite 生成产物，不作为前端源码手工维护。
- Vite 使用 `/api` 代理 FastAPI；生产由 FastAPI 提供 SPA fallback。
- 普通用户运行不依赖 Node/npm。
- UI 架构变更必须同步更新 `docs/ui-architecture.md`。

## 12. 当前开发优先级

1. 真实 PDD capability probe 与字段校准。
2. 商品/SKU/订单/售后稳定 ETL。
3. 报表字段映射和数据质量。
4. 趋势变化点、SKU 蚕食和趋势/诊断优先级融合。
5. AI 结构化行动计划和复盘。
6. 图片分析/生成工作流。
7. 多平台 Release 稳定性、签名/公证、备份和数据库 migration。
