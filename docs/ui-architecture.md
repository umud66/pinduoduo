# 前端 UI 架构

## 当前技术栈

前端统一采用 Vue 3、Vite、Vue Router、Pinia 和原生 Fetch API。Node.js/npm 是开发与构建依赖，不是最终用户运行依赖。

## 源码目录

```text
frontend/src/
├── api/             按业务域封装 HTTP
├── components/
│   ├── data/        同步、能力探针、Browser Data Bridge、报表导入
│   ├── diagnosis/   确定性诊断展示
│   ├── insights/    趋势、同商品静态对比
│   ├── decision/    变化点、结构迁移、action_priority
│   ├── optimization/优化任务、执行记录、复盘时间线
│   └── settings/    拼多多应用/店铺授权等复杂设置域
├── layouts/         页面骨架
├── router/          路由
├── stores/          跨页面共享状态
├── styles/          全局与领域样式
└── views/           路由页面
```

## 页面路由

`/dashboard`、`/skus`、`/tasks`、`/data`、`/ai`、`/settings` 是独立路由。Vue Router 使用 history 模式，FastAPI 对非 `/api` 路径执行 SPA fallback。

## 分层职责

- `views/`：路由级页面，只负责页面编排和生命周期。
- `components/`：可复用领域组件；复杂领域继续使用子目录拆分。
- `api/`：集中维护 API URL 和通用请求错误处理。
- `stores/`：只保存跨页面共享状态。
- `router/`：主路由和元信息。

SKU 详情继续按决策、趋势、诊断、优化任务拆分，不在 Drawer 中重复实现算法。

设置页：

```text
SettingsView.vue
├── 店铺基本信息
├── components/settings/PddAuthorizationSettings.vue
└── AI Provider 管理
```

数据中心：

```text
DataCenterView.vue
├── SyncCenter.vue
├── CapabilityProbe.vue
├── BrowserDataBridge.vue      实验分支
└── ReportImport.vue
```

`BrowserDataBridge.vue` 只负责：

```text
启动/停止浏览器采集
显示 Playwright 可用状态
选择起始 URL / allowlist
轮询采集会话
展示脱敏后的响应摘要
```

它不得直接解析拼多多私有响应为正式订单、SKU、流量或推广指标。正式字段映射只能由 Python Adapter 完成。

领域样式分别使用 `styles/decision-support.css`、`styles/optimization.css`、`styles/pdd-auth.css`、`styles/browser-bridge.css`，不继续向全局 `app.css` 无限追加。

## 业务与安全边界

Vue 不实现诊断、趋势、决策、复盘、OAuth Token 交换或浏览器私有响应业务映射。

```text
Python 服务统一计算 / Token 交换 / 网络响应过滤与脱敏
→ API 只返回必要结构化状态
→ Vue 负责展示和用户主动操作
```

Access Token、Refresh Token、Client Secret、Cookie、Authorization 请求头、密码和验证码不得从 API 回显到 Vue。

Browser Data Bridge UI 默认不请求完整 response body，只展示发现摘要。

## 构建与运行

主线开发：Vite `:5173` + FastAPI `:8765`。

Browser Data Bridge 实验环境额外需要：

```text
Python optional dependency: playwright
Chromium browser binary
```

实验分支尚未把 Chromium 加入正式多平台 Release。正式主线仍保持 `npm run build -> app/static/ -> PyInstaller -> 多平台 Release`。

## 强制规则

1. 新主页面必须建立独立 `views/*View.vue`。
2. View 出现多个独立业务工作区必须拆领域组件。
3. API 调用必须放 `src/api/`。
4. 跨页面共享状态才进入 Pinia。
5. 业务公式只能由后端服务实现，Vue 不复制算法。
6. 拼多多授权 UI 放 `components/settings/`。
7. 普通商家流程不得要求手工 Access Token。
8. Browser Data Bridge UI 放 `components/data/`，不得把 Playwright/网络解析逻辑放进 Vue。
9. Browser Data Bridge 不显示 Cookie、Authorization、请求体或未经脱敏的 response body。
10. 领域样式明显增长时拆独立 CSS。
11. 不允许重新退化为单个超大 `.vue` / `.js` / CSS 文件。
12. `app/static/` 是 Vite 生成产物，不作为源码手工维护。
13. Browser 实验正式进入 Release 前必须单独评估 Chromium 体积、平台支持和打包流程。
14. UI 架构或组件职责变化必须在同一大功能提交中更新本文。
