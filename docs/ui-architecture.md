# 前端 UI 架构

## 当前技术栈

前端统一采用 Vue 3、Vite、Vue Router、Pinia 和原生 Fetch API。Node.js/npm 是开发与构建依赖，不是最终用户运行依赖。

## 源码目录

```text
frontend/src/
├── api/             按业务域封装 HTTP
├── components/
│   ├── data/        同步、能力探针、报表导入
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

设置页当前拆分：

```text
SettingsView.vue
├── 店铺基本信息
├── components/settings/PddAuthorizationSettings.vue
└── AI Provider 管理
```

`PddAuthorizationSettings.vue` 负责：

```text
开放平台应用 Client ID/Secret/redirect_uri
→ 发起店铺授权
→ 授权状态轮询
→ 本地 callback / 手工 code 开发兜底
→ refresh
→ capability probe
→ 断开本机授权
```

普通商家 UI 不再显示“手工填写 Access Token”。

领域样式分别使用 `styles/decision-support.css`、`styles/optimization.css`、`styles/pdd-auth.css`，不继续向全局 `app.css` 无限追加。

## 业务与安全边界

Vue 不实现诊断、趋势、决策、复盘或 OAuth Token 交换算法。

```text
Python 服务统一计算 / 交换 Token
→ API 只返回脱敏结构化状态
→ Vue 负责展示和用户交互
```

Access Token、Refresh Token、Client Secret 不得从 API 回显到 Vue。

## 构建与运行

开发：Vite `:5173` + FastAPI `:8765`，`/api` 代理后端。

正式：`npm run build -> app/static/ -> PyInstaller -> 多平台 Release`。

## 强制规则

1. 新主页面必须建立独立 `views/*View.vue`。
2. View 出现多个独立业务工作区必须拆领域组件。
3. API 调用必须放 `src/api/`。
4. 跨页面共享状态才进入 Pinia。
5. 业务公式只能由后端服务实现，Vue 不复制算法。
6. 拼多多授权 UI 放 `components/settings/`，不得回退成 SettingsView 内的一大段表单逻辑。
7. 普通商家流程不得要求手工 Access Token；手工 code 只能放开发兜底区域。
8. 领域样式明显增长时拆独立 CSS，禁止重新形成一个超大 `app.css`。
9. 不要求最终用户安装 Node.js。
10. 修改前端依赖、Vite 输出、SPA fallback 或 PyInstaller 静态路径时必须同时验证 Release workflow。
11. UI 架构或组件职责变化必须在同一大功能提交中更新本文。
