# Pinduoduo AI Operator

面向拼多多中小商家的本地化 AI 运营诊断工具。目标是 **低门槛、一键启动、本地 SQLite、拼多多 API + 商家报表双通道、可替换 AI Provider，并支持图片生成**。

> 当前处于 MVP 开发阶段。拼多多开放平台实际权限以应用审核和店铺授权 scope 为准；曝光、点击、推广等指标不能假定必然可由 API 获取。

## 普通用户体验

1. 下载对应操作系统 Release。
2. Windows 解压运行 `PDD运营助手.exe`；macOS 打开 `PDD运营助手.app`；Linux 解压运行 `PDD-AI-Operator`。
3. 浏览器自动打开本地运营工作台。
4. 配置拼多多授权和 AI Provider。
5. 同步/导入数据并进行 SKU 诊断。

最终用户不需要安装 PostgreSQL、Redis、Docker、Python、Node.js/npm。

## 技术路线

### 后端

- Python 3.11+
- FastAPI
- SQLite + SQLAlchemy
- httpx
- openpyxl
- cryptography
- PyInstaller

### 前端

- Vue 3
- Vite
- Vue Router
- Pinia

Node.js/npm 只用于开发和 Release 构建。Vite 产物输出到 `app/static/`，再由 FastAPI/PyInstaller 托管和打包。

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
AI 运营建议
        ↓
人工执行与后续复盘
```

当前 SKU 分析已经支持：

- 今日 vs 前 7 日平均。
- 最近 7 日 vs 前 7 日。
- 最近 30 个真实数据日趋势。
- 同商品 SKU 最近 7 日 GMV 排名和贡献占比。
- SKU 贡献集中度 HHI。
- 当前诊断问题连续出现天数。
- GMV 经营变化点识别。
- 商品整体稳定时的 SKU 份额迁移/蚕食候选。
- 不覆盖 `priority_score` 的可解释 `action_priority`。
- 店铺级下滑 SKU 趋势概览。

## 前端路由

```text
/dashboard   经营总览
/skus        SKU 诊断与趋势工作台
/data        数据中心
/ai          AI 工作台
/settings    设置
```

## 开发启动

需要 Python 3.11+ 和 Node.js 22+：

```bash
python -m venv .venv
pip install -e ".[dev]"
python scripts/dev.py
```

`scripts/dev.py` 会启动 FastAPI `:8765` 和 Vite `:5173`，浏览器打开 Vite 页面，`/api` 自动代理到 FastAPI。

## 构建与 Release

正式 Release 由 `.github/workflows/release.yml` 在原生 Runner 上构建：

- Windows x64
- Linux x64
- macOS Apple Silicon arm64
- macOS Intel x64

平台构建脚本：

```text
scripts/build_windows.ps1
scripts/build_unix.sh
```

## 设计原则

- 数据先标准化，再做诊断，最后交给 LLM 解释。
- 缺失数据保持 unknown/None，不允许伪造成 0。
- 比率指标跨天聚合必须使用分子/分母重新计算，禁止简单平均每日百分比。
- 变化点与 SKU 份额迁移只作为经营证据，不描述成已证明的因果关系。
- `action_priority` 只能在 `priority_score` 上增加可解释上下文，不允许回写替换历史诊断分数。
- 拼多多权限不足时仍可通过报表导入继续使用。
- 用户敏感订单信息默认不发送给 AI Provider。
- 模型统一走 Provider/Gateway。
- 提交按“大功能”组织，不按文件机械拆 commit。
- 架构、数据口径、诊断/趋势/决策支持规则、发布规则和工程规则变化时，必须在同一功能提交中同步维护文档。

## 文档

- `docs/product-discussion.md`：产品与技术讨论纪要。
- `docs/functional-spec.md`：详细功能说明与验收基线。
- `docs/frontend-migration.md`：Vue 3 迁移决策与验收条件。
- `docs/ui-architecture.md`：当前 Vue 前端架构与强制约束。
- `docs/diagnosis-engine.md`：SKU 单日诊断、GMV 拆解、影响度、置信度和 `priority_score`。
- `docs/trend-analysis.md`：时间窗口、趋势比较、同商品 SKU 对比、HHI 和异常持续时间口径。
- `docs/decision-support.md`：GMV 变化点、SKU 份额迁移候选与 `action_priority` 规则。
- `docs/pdd-sync.md`：拼多多同步与恢复机制。
- `docs/platform-support.md`：Windows/macOS/Linux 平台支持状态。
- `docs/deployment.md`：部署原则。
- `docs/release.md`：多平台 Release 流程。
- `AGENTS.md`：后续编码 Agent 工程规则。
