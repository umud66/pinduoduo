# Vue 3 前端迁移记录

## 决策

自 0.4 开发线起，前端从“单个 HTML + 原生 ES Modules”迁移为 Vue 3 SPA。

## 原因

原方案随着功能增长出现页面生命周期手工控制、路由不是真正页面模型、组件复用成本增大、数据中心持续膨胀等维护风险。

## 保留不变的约束

- FastAPI 仍是唯一后端服务。
- SQLite 仍为默认数据库。
- 最终用户不安装 Node.js/npm。
- Windows 仍为下载后双击 EXE 使用。
- 拼多多与 AI API 协议不因前端迁移改变。

## 迁移后的开发边界

- 页面：`frontend/src/views/`
- 领域组件：`frontend/src/components/`
- HTTP：`frontend/src/api/`
- 全局状态：`frontend/src/stores/`
- 路由：`frontend/src/router/`
- 后端构建产物：`app/static/`

## 发布链变化

GitHub Actions 提供 Node.js 22 构建环境。`scripts/build_windows.ps1` 负责执行 Vue 构建，再执行 PyInstaller。正式 Release 仍只分发 Windows ZIP，不分发 `node_modules`。

## 验收条件

- `/dashboard`、`/skus`、`/data`、`/ai`、`/settings` 是独立路由。
- 直接刷新路由不会 404。
- 店铺切换由 Pinia 管理。
- 数据中心同步、能力探针、报表导入保持独立组件。
- SKU 详情和诊断面板保持独立组件。
- Release Action 完成 Vue build + pytest + PyInstaller + Release。
