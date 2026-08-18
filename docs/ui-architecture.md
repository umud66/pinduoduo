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
│   └── decision/    变化点、结构迁移、action_priority
├── layouts/         页面骨架
├── router/          路由
├── stores/          跨页面共享状态
├── styles/          全局与领域样式
└── views/           路由页面
```

## 页面路由

`/dashboard`、`/skus`、`/data`、`/ai`、`/settings` 是独立路由。Vue Router 使用 history 模式，FastAPI 对非 `/api` 路径执行 SPA fallback。

## 分层职责

- `views/`：路由级页面，只负责页面编排和生命周期。
- `components/`：可复用领域组件；复杂领域继续使用子目录拆分。
- `api/`：集中维护 API URL 和通用请求错误处理。
- `stores/`：只保存跨页面共享状态。
- `router/`：主路由和元信息。

SKU 详情当前组合：

```text
SkuDrawer.vue
├── components/decision/DecisionSupportPanel.vue
├── components/insights/SkuTrendPanel.vue
├── components/insights/PeerComparison.vue
└── components/diagnosis/DiagnosisPanel.vue
```

决策支持继续拆分：

```text
components/decision/
├── DecisionSupportPanel.vue      只负责组合
├── ActionPriorityCard.vue        行动优先级与加分依据
├── ChangePointPanel.vue          GMV 变化点
└── StructureShiftPanel.vue       商品内 SKU 份额迁移候选
```

领域样式使用 `styles/decision-support.css`，不继续向全局 `app.css` 无限追加。

## 业务计算边界

Vue 不实现诊断、趋势和决策公式。

错误做法：

```text
Vue 自己计算 CTR / HHI / 变化点 / action_priority / 蚕食判断
```

正确做法：

```text
Python 服务统一计算
→ API 返回结构化结果
→ Vue 负责展示、交互和状态
```

这样 Dashboard、SKU 详情、AI Prompt 和后续任务系统不会出现不同计算口径。

## 构建与运行

开发：Vite `:5173` + FastAPI `:8765`，`/api` 代理后端。

正式：

```text
npm run build
→ app/static/
→ PyInstaller
→ 多平台 Release
```

`app/static/` 是生成产物，不作为手工维护源码。

## 强制规则

1. 新主页面必须建立独立 `views/*View.vue`。
2. View 出现多个独立业务工作区必须拆领域组件。
3. API 调用必须放 `src/api/`。
4. 跨页面共享状态才进入 Pinia。
5. 业务公式只能由后端服务实现，Vue 不复制算法。
6. 领域样式明显增长时拆独立 CSS，禁止重新形成一个超大 `app.css`。
7. 不要求最终用户安装 Node.js。
8. 修改前端依赖、Vite 输出、SPA fallback 或 PyInstaller 静态路径时必须同时验证 Release workflow。
9. UI 架构或组件职责变化必须在同一大功能提交中更新本文。
