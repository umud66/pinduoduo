# Pinduoduo AI Operator

面向拼多多中小商家的本地化 AI 运营诊断工具。目标是 **低门槛、一键启动、本地 SQLite、拼多多 API + 商家报表双通道、可替换 AI Provider，并支持图片生成**。

> 当前处于 MVP 开发阶段。拼多多开放平台实际权限以应用审核和店铺授权 scope 为准；曝光、点击、推广等指标不能假定必然可由 API 获取。

## 普通用户体验

1. 下载对应操作系统 Release。
2. Windows 解压运行 `PDD运营助手.exe`；macOS 打开 `PDD运营助手.app`；Linux 解压运行 `PDD-AI-Operator`。
3. 浏览器自动打开本地运营工作台。
4. 配置拼多多开放平台应用，并通过拼多多官方授权页绑定店铺。
5. 配置 AI Provider。
6. 同步/导入数据并进行 SKU 诊断、优化执行和效果复盘。

普通用户不需要手工填写 Access Token，也不需要安装 PostgreSQL、Redis、Docker、Python、Node.js/npm。

## 拼多多授权模型

```text
开放平台应用
Client ID + Client Secret
        ↓
拼多多官方店铺授权页
        ↓
商家确认
        ↓
code + state
        ↓
Token create / refresh
        ↓
owner / scope / access_token
        ↓
capability probe
        ↓
商品 / 订单 / 售后同步
```

当前授权实现状态为 `adapted`：代码已经按现行 OpenAPI SDK 常见协议结构适配，但还没有使用本项目自己的真实审核应用和真实授权店铺把授权 URL、localhost callback、Token refresh、scope 等逐项升级为 `verified`。

## 当前核心工作流

```text
PDD API / 商家报表
        ↓
SKU Daily Metric
        ↓
单日确定性诊断
        ↓
趋势与同商品 SKU 对比
        ↓
变化点 / 商品内份额迁移候选
        ↓
priority_score + 可解释趋势上下文
        ↓
action_priority
        ↓
选择具体动作创建优化任务
        ↓
执行并记录
        ↓
3 / 7 / 14 日指标复盘
        ↓
形成可复用运营证据
```

## 前端路由

```text
/dashboard   经营总览
/skus        SKU 诊断与趋势工作台
/tasks       优化任务与效果复盘
/data        数据中心
/ai          AI 工作台
/settings    设置 / 拼多多店铺授权
```

## 技术路线

后端：Python 3.11+、FastAPI、SQLite + SQLAlchemy、httpx、openpyxl、cryptography、PyInstaller。

前端：Vue 3、Vite、Vue Router、Pinia。Node.js/npm 只用于开发和 Release 构建。

## 开发启动

需要 Python 3.11+ 和 Node.js 22+：

```bash
python -m venv .venv
pip install -e ".[dev]"
python scripts/dev.py
```

## 构建与 Release

正式 Release 由 `.github/workflows/release.yml` 在原生 Runner 上构建 Windows x64、Linux x64、macOS arm64、macOS Intel x64。

## 设计原则

- 应用身份与店铺授权分开建模；Client ID/Secret 不代表店铺已经授权。
- 普通商家不手工维护 Access Token。
- Token/Secret 加密落库，不回显前端、不写日志。
- Token 生命周期只使用平台返回字段，不自行假设有效期。
- 数据先标准化，再做诊断，最后交给 LLM 解释。
- 缺失数据保持 unknown/None，不允许伪造成 0。
- 比率指标跨天必须重新聚合分子/分母。
- 变化点与 SKU 份额迁移只作为经营证据，不描述成已证明因果。
- `action_priority` 不回写替换 `priority_score`。
- 优化复盘只描述执行前后的关联变化。
- 拼多多权限不足时仍可通过报表导入继续使用。
- 提交按“大功能”组织，不按文件机械拆 commit。
- 架构、授权/API、数据口径、诊断/趋势/决策支持/复盘规则、发布规则和工程规则变化时，必须在同一功能提交中同步维护文档。

## 文档

- `docs/product-discussion.md`：产品与技术讨论纪要。
- `docs/functional-spec.md`：详细功能说明与验收基线。
- `docs/frontend-migration.md`：Vue 3 迁移决策。
- `docs/ui-architecture.md`：Vue 前端架构与强制约束。
- `docs/pdd-authorization.md`：开放平台应用、店铺授权、Token 生命周期与真实验证清单。
- `docs/pdd-sync.md`：拼多多同步与恢复机制。
- `docs/diagnosis-engine.md`：确定性诊断与 `priority_score`。
- `docs/trend-analysis.md`：趋势与同商品比较口径。
- `docs/decision-support.md`：变化点、份额迁移与 `action_priority`。
- `docs/optimization-loop.md`：优化任务、执行记录、3/7/14 日复盘和因果边界。
- `docs/platform-support.md`：多平台支持状态。
- `docs/deployment.md`：部署原则。
- `docs/release.md`：多平台 Release 流程。
- `AGENTS.md`：后续编码 Agent 工程规则。
