# Pinduoduo AI Operator

面向拼多多中小商家的本地化 AI 运营诊断工具。目标是 **低门槛、一键启动、本地 SQLite、拼多多 API + 商家报表双通道、可替换 AI Provider，并支持图片生成**。

> 当前处于 MVP 开发阶段。拼多多开放平台实际权限以应用审核和店铺授权 scope 为准；曝光、点击、推广等指标不能假定必然可由 API 获取。

## 当前实验分支

`experiment/browser-data-bridge` 用于验证在无法取得开放平台资质/Token 时，通过**用户可见的持久化 Chromium 浏览器观察商家后台页面自身网络响应**作为备用数据通道。

```text
用户自行登录商家后台
        ↓
页面正常请求数据
        ↓
Browser Data Bridge 观察 JSON response
        ↓
域名过滤 + 脱敏 + 候选分类
        ↓
响应发现层
        ↓
后续专用 Adapter
        ↓
正式标准模型
```

该实验不会读取/保存密码、验证码、Cookie、Authorization 请求头或请求体，也不会导出 Cookie 后脱离浏览器伪造后台请求。未知私有响应目前不会直接写入正式订单/SKU/指标表。详细规则见 `docs/browser-data-bridge.md`。

Browser 依赖为可选项：

```bash
pip install -e ".[dev,browser]"
playwright install chromium
```

没有安装 Browser 依赖时，原 OpenAPI、报表、诊断、优化任务功能仍可运行。

## 普通用户主线体验

1. 下载对应操作系统 Release。
2. Windows 解压运行 `PDD运营助手.exe`；macOS 打开 `PDD运营助手.app`；Linux 解压运行 `PDD-AI-Operator`。
3. 浏览器自动打开本地运营工作台。
4. 配置拼多多开放平台应用，并通过拼多多官方授权页绑定店铺。
5. 配置 AI Provider。
6. 同步/导入数据并进行 SKU 诊断、优化执行和效果复盘。

普通用户不需要手工填写 Access Token，也不需要安装 PostgreSQL、Redis、Docker、Python、Node.js/npm。

## 数据来源策略

```text
优先：PDD OpenAPI
        ↓ 不可用/权限不足
备用：商家官方导出报表
        ↓ 实验
Browser Data Bridge
```

Browser Data Bridge 当前只是实验发现层，不能替代官方 OpenAPI 的稳定性和权限语义。

## 当前核心工作流

```text
PDD API / 商家报表 / 实验 Browser Adapter
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
```

## 前端路由

```text
/dashboard   经营总览
/skus        SKU 诊断与趋势工作台
/tasks       优化任务与效果复盘
/data        数据中心 / Browser Data Bridge 实验
/ai          AI 工作台
/settings    设置 / 拼多多店铺授权
```

## 技术路线

后端：Python 3.11+、FastAPI、SQLite + SQLAlchemy、httpx、openpyxl、cryptography、PyInstaller。

前端：Vue 3、Vite、Vue Router、Pinia。

实验 Browser Data Bridge：Playwright Python + headed Chromium + persistent context。

## 开发启动

主线开发：

```bash
python -m venv .venv
pip install -e ".[dev]"
python scripts/dev.py
```

Browser 实验：

```bash
pip install -e ".[dev,browser]"
playwright install chromium
python scripts/dev.py
```

## 构建与 Release

正式 Release 仍由 `.github/workflows/release.yml` 构建 Windows x64、Linux x64、macOS arm64、macOS Intel x64。

**Browser Data Bridge 实验尚未进入正式 Release 打包。** 在真实商家验证和体积评估完成前，不把 Chromium 强行加入正式安装包。

## 设计原则

- 应用身份与店铺授权分开建模。
- 普通商家不手工维护 Access Token。
- Token/Secret 加密落库，不回显前端、不写日志。
- Browser 实验不导出 Cookie，不保存登录密码/验证码，不绕过平台访问控制。
- Browser 私有响应必须经过“发现 -> 稳定验证 -> Adapter -> 测试”后才能进入标准模型。
- 数据先标准化，再做诊断，最后交给 LLM 解释。
- 缺失数据保持 unknown/None，不允许伪造成 0。
- 提交按“大功能”组织，不按文件机械拆 commit。
- 架构、授权/API、Browser 数据规则、数据口径、诊断/趋势/决策/复盘规则变化时必须同步维护文档。

## 文档

- `docs/browser-data-bridge.md`：浏览器网络响应实验架构、安全边界和合并条件。
- `docs/pdd-authorization.md`：开放平台应用、店铺授权、Token 生命周期。
- `docs/pdd-sync.md`：拼多多 OpenAPI 同步与恢复机制。
- `docs/ui-architecture.md`：Vue 前端架构与强制约束。
- `docs/diagnosis-engine.md`：确定性诊断与 `priority_score`。
- `docs/trend-analysis.md`：趋势与同商品比较口径。
- `docs/decision-support.md`：变化点、份额迁移与 `action_priority`。
- `docs/optimization-loop.md`：优化任务与 3/7/14 日复盘。
- `docs/platform-support.md`：多平台支持状态。
- `docs/release.md`：多平台 Release 流程。
- `AGENTS.md`：后续编码 Agent 工程规则。
