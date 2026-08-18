# 前端 UI 架构

## 当前技术栈

前端统一采用 Vue 3、Vite、Vue Router、Pinia 和原生 Fetch API。Node.js/npm 是开发与构建依赖，不是最终用户运行依赖。Windows Release 构建时由 GitHub Actions 生成 `app/static/`，随后由 PyInstaller 一并打包。

## 为什么迁移到 Vue

原生 HTML + ES Modules 适合早期 MVP，但随着 Dashboard、SKU 诊断、同步中心、AI 工作台、设置和详情抽屉增长，页面状态、路由、组件复用和跨页面数据刷新需要明确的组件模型和状态管理。

## 源码目录

```text
frontend/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.js
    ├── App.vue
    ├── router/
    ├── stores/
    ├── api/
    ├── layouts/
    ├── views/
    ├── components/
    │   ├── data/
    │   └── diagnosis/
    └── styles/
```

## 页面路由

`/dashboard`、`/skus`、`/data`、`/ai`、`/settings` 是独立路由。Vue Router 使用 history 模式，FastAPI 对非 `/api` 路径执行 SPA fallback。

## 分层职责

- `views/`：路由级页面，负责页面编排和页面级生命周期。
- `components/`：可复用领域组件；复杂领域继续按目录拆分。
- `api/`：按业务域封装 HTTP 调用，页面禁止散落 URL 与通用错误解析。
- `stores/`：只保存跨页面共享状态，例如当前店铺、Provider、全局同步状态。
- `router/`：集中维护主路由和元信息。

## 构建与运行

开发环境：Vite `:5173`，FastAPI `:8765`，Vite `/api` 代理后端。

正式构建：

```text
frontend npm run build
        ↓
app/static/index.html + assets/
        ↓
PyInstaller
        ↓
Windows Release
```

`app/static/` 是生成产物，不作为手工维护的源码目录。

## 强制规则

1. 新主页面必须创建独立 `views/*View.vue`。
2. 复杂页面使用领域组件拆分，不允许把全部功能堆进单个 View。
3. API 调用必须放入 `src/api/`。
4. 跨页面状态才进入 Pinia。
5. 不允许重新把业务实现写入 `index.html`。
6. 不要求最终用户安装 Node.js。
7. 修改前端依赖、Vite 输出目录、FastAPI SPA fallback 或 PyInstaller 静态资源路径时，必须同时验证 Release workflow。
8. 架构规则改变时必须在同一大功能提交中更新本文件和 `AGENTS.md`。
