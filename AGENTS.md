# AGENTS.md

本文件约束所有后续在本仓库工作的编码 Agent。项目目标是“普通拼多多商家可一键部署的本地 AI 运营诊断与优化闭环工具”。

## 1. 产品与部署目标

- 本地优先，面向非技术商家。
- 正式发布支持 Windows、macOS、Linux。
- SQLite 默认存储，不要求 PostgreSQL、Redis、Docker。
- 拼多多 API 与报表导入并存。
- SKU 诊断由程序确定性计算，LLM 负责解释和补充建议。
- 优化动作必须由用户明确选择/执行，AI 不得直接写店铺状态。
- 正式用户路径保持：`下载 -> 解压/打开应用 -> 浏览器打开 -> 配置 -> 使用`。
- 开发环境允许 Python/Node.js，正式发布包不得要求最终用户安装它们。

## 2. 后端架构边界

- `app/services/pdd/`：拼多多 Gateway、签名、接口、分页、错误和原始响应。
- `app/db/`：平台数据标准化、本地任务/复盘模型；本地模型是分析主来源。
- `app/services/diagnosis/`：确定性单日诊断，缺失数据保持 `None/unknown`。
- `app/services/trends.py`：纯趋势/窗口/同商品比较算法，不访问数据库。
- `app/services/insights.py`：从数据库组织趋势、同商品 SKU、持续时间等经营洞察。
- `app/services/decision_support.py`：变化点、结构迁移和 `action_priority` 等决策支持。
- `app/services/optimization.py`：优化任务生命周期、基线冻结和复盘数据组织。
- `app/services/optimization_review.py`：纯复盘指标映射和效果比较算法。
- `app/services/ai/`：所有模型调用经 Provider/Gateway。

业务公式不得复制到 API 层或 Vue 层。

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

- API Key 加密落库。
- 消费者姓名、电话、地址默认不发送 AI。
- AI 输出不得直接驱动订单、退款、改价、上下架、库存等写操作。
- AI 只能解释系统已有数据、提出候选动作；用户必须明确确认并自行执行店铺变更。

## 6. 诊断、趋势与决策规则

每条诊断规则至少定义稳定 code、category、severity、样本门槛、当前/基线/变化、impact_score、confidence、priority_score、actions、validation_metrics 和单元测试。

修改诊断阈值、基线算法、健康分、GMV 拆解或优先级公式时，必须同步更新 `docs/diagnosis-engine.md` 和必要的 `docs/functional-spec.md`。

趋势分析必须遵守：时间窗口以 SKU 最新真实数据日为锚点；CTR/CVR/退款率/ROI 跨日重新聚合分子/分母；缺失数据保持 unknown；30 日图不补造日期；同商品排名使用同窗口真实数据；异常持续时间遇到日期缺口必须中断。修改这些口径时同步更新 `docs/trend-analysis.md` 和测试。

决策支持必须遵守：

- `priority_score` 保持单次确定性诊断语义。
- `action_priority` 只能在 `priority_score` 上叠加可解释上下文，不得回写覆盖历史诊断分数。
- 变化点和商品内 SKU 份额迁移只能描述为经营证据/候选，不得描述成确定因果。
- 修改变化点阈值、迁移候选阈值、加分规则或上限时，同步更新 `docs/decision-support.md` 和测试。

## 7. 优化任务与复盘规则

优化闭环以 `docs/optimization-loop.md` 为详细口径。必须长期保持：

```text
诊断动作
→ 创建任务 planned
→ start 冻结执行前 7 日基线
→ in_progress
→ complete 记录实际执行内容
→ 3/7/14 日复盘
```

硬性规则：

- 基线窗口为执行日 `D` 的 `D-7 ... D-1`，不得把执行当天混入基线。
- 复盘窗口为 `D+1 ... D+N`，N 当前固定 3/7/14。
- 缺失日期不补 0。
- 复盘窗口至少要求约 60% 真实数据覆盖；不足时为 `insufficient_data`。
- 基线为 0 时不得伪造百分比提升。
- 退款率是反向指标，下降才算改善。
- 自动效果判断只使用有稳定本地口径的验证指标；无法计算的文本指标不得伪造。
- 复盘只描述执行前后“关联变化”，不得声称动作已被证明造成结果。
- Vue 不得计算复盘 `effect_score/outcome`。
- 修改窗口、覆盖率、指标映射、±5% 效果阈值或因果表述规则时，必须同步更新 `docs/optimization-loop.md` 和测试。

## 8. Git 提交规范

**必须按大功能提交，不按文件提交。** 一个功能涉及源码、测试、API、数据库、Vue、构建脚本和文档时，应按业务边界形成少量完整 commit，禁止机械文件提交。

## 9. 测试规则

后端至少运行 `python -m compileall app scripts tests` 与 `pytest`；前端至少运行 `npm install/npm ci` 与 `npm run build`。无法执行必须明确记录环境限制，不得声称通过。

算法优先写纯函数测试，至少覆盖缺失值、窗口边界、比率聚合、同商品结构、连续日期、复盘反向指标、基线为 0 和数据覆盖不足。

涉及 Release/平台的改动必须通过原生 GitHub Runner 验证对应 PyInstaller 构建。

## 10. Release 规则

- 正式 Release 统一由 `.github/workflows/release.yml` 构建。
- 当前稳定矩阵：Windows x64、Linux x64、macOS arm64、macOS Intel x64。
- Release 必须先运行 Python 测试与 Vue build，再执行平台矩阵。
- Windows 使用 `scripts/build_windows.ps1`；Linux/macOS 使用 `scripts/build_unix.sh`。
- 每个平台产生独立 SHA256，最终 Release 包含 `SHA256SUMS.txt`。
- 矩阵 job 只构建临时 artifact，只能由单独 `publish` job 创建/更新 GitHub Release。
- macOS Developer ID 签名/notarization 未配置前，禁止声称已签名。

## 11. 文档是实现的一部分

以下改动必须在同一大功能 commit 中形成或更新文档：架构/技术栈、模块边界、数据结构/字段口径、PDD API 状态、诊断/趋势/决策/复盘规则、UI 主流程、发布部署、安全隐私、Git/测试/Agent 工程规则。

文档入口：

- 产品决策：`docs/product-discussion.md` 或独立专题文档。
- 功能验收：`docs/functional-spec.md`。
- UI：`docs/ui-architecture.md`。
- 诊断：`docs/diagnosis-engine.md`。
- 趋势：`docs/trend-analysis.md`。
- 决策支持：`docs/decision-support.md`。
- 优化闭环：`docs/optimization-loop.md`。
- 同步：`docs/pdd-sync.md`。
- 发布：`docs/release.md`、`docs/platform-support.md`。

如果代码与文档冲突，提交不得视为完整。

## 12. Vue 前端强制架构

前端源码位于 `frontend/`，统一使用 Vue 3 + Vite + Vue Router + Pinia。

```text
frontend/src/
├── api/
├── components/
│   ├── data/
│   ├── diagnosis/
│   ├── insights/
│   ├── decision/
│   └── optimization/
├── layouts/
├── router/
├── stores/
├── styles/
└── views/
```

- `index.html` 只能作为 Vite 挂载入口。
- 新主页面建立独立 `*View.vue` 和路由。
- View 只做页面编排；多个独立工作区拆到 `components/<domain>/`。
- 趋势放 `components/insights/`，决策支持放 `components/decision/`，优化任务与复盘放 `components/optimization/`。
- API URL 和通用请求错误处理集中到 `src/api/`。
- Pinia 只保存真正跨页面共享状态。
- 不允许重新退化为单个超大 `.vue` / `.js` / CSS 文件。
- 复杂新样式使用独立领域 CSS，不继续无限增长 `app.css`。
- `app/static/` 是 Vite 生成产物，不作为源码手工维护。
- 普通用户运行不依赖 Node/npm。
- UI 架构变更必须同步更新 `docs/ui-architecture.md`。

## 13. 当前开发优先级

1. 真实 PDD capability probe 与字段校准。
2. 商品/SKU/订单/售后稳定 ETL 与数据质量。
3. 优化任务 3/7/14 日真实商家复盘校准。
4. AI 将确定性诊断转换为结构化候选行动计划，但仍需人工确认。
5. 从历史优化任务提炼可解释的本地运营知识库。
6. 图片分析/生成工作流。
7. 多平台 Release 稳定性、macOS 签名/公证、备份和正式数据库 migration。
