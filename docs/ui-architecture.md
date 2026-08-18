# 前端 UI 架构

## 当前技术栈

前端统一采用 Vue 3、Vite、Vue Router、Pinia 和原生 Fetch API。Node.js/npm 是开发与构建依赖，不是最终用户运行依赖。正式 Release 在各平台 GitHub Runner 上生成 `app/static/`，随后由 PyInstaller 打包。

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
    │   ├── diagnosis/
    │   └── insights/
    └── styles/
        ├── base.css
        ├── app.css
        └── trends.css
```

## 页面路由

`/dashboard`、`/skus`、`/data`、`/ai`、`/settings` 是独立路由。Vue Router 使用 history 模式，FastAPI 对非 `/api` 路径执行 SPA fallback。

## 分层职责

- `views/`：路由级页面，负责页面编排和页面级生命周期。
- `components/`：可复用领域组件；复杂领域继续按目录拆分。
- `components/data/`：同步、能力探针、报表等数据接入组件。
- `components/diagnosis/`：确定性诊断展示组件。
- `components/insights/`：趋势、窗口对比、同商品 SKU 对比、图表和变化标签；这里只展示后端计算结果，不复制统计口径。
- `api/`：按业务域封装 HTTP 调用，页面禁止散落 URL 与通用错误解析。
- `stores/`：只保存跨页面共享状态，例如当前店铺、Provider、全局同步状态。
- `router/`：集中维护主路由和元信息。

## SKU 诊断页面结构

`SkuDiagnosisView.vue` 负责：

```text
店铺级趋势概览
+ 搜索/筛选
+ SKU 列表
+ 打开 SKU Drawer
```

趋势概览由 `TrendOverview.vue` 实现。

`SkuDrawer.vue` 负责组合，不自行计算趋势：

```text
SKU 基础信息
  ↓
SkuTrendPanel.vue
  ↓
PeerComparison.vue
  ↓
DiagnosisPanel.vue
  ↓
AI 建议动作
```

趋势领域继续拆为：

```text
components/insights/
├── TrendDelta.vue
├── MetricTrendChart.vue
├── TrendOverview.vue
├── SkuTrendPanel.vue
└── PeerComparison.vue
```

## 业务计算边界

Vue 不计算经营统计口径。

例如以下逻辑必须由后端 `app/services/trends.py` / `app/services/insights.py` 计算：

- 今日 vs 7 日均值。
- 最近 7 日 vs 前 7 日。
- CTR/CVR/退款率/ROI 的跨日聚合。
- 同商品 SKU GMV 排名与占比。
- HHI。
- 异常连续天数。

Vue 只负责格式化和展示。这样可保证 Dashboard、SKU 页面和后续 AI Context 使用同一口径。

## 样式规则

通用布局与历史组件样式保留在 `app.css`。

趋势域新增 `trends.css`，后续某个业务域出现较多专有样式时建立自己的 CSS 文件，禁止继续无限向一个全局 CSS 文件追加。

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
Windows / macOS / Linux Release
```

`app/static/` 是生成产物，不作为手工维护的源码目录。

## 强制规则

1. 新主页面必须创建独立 `views/*View.vue`。
2. 复杂页面使用领域组件拆分，不允许把全部功能堆进单个 View。
3. API 调用必须放入 `src/api/`。
4. 跨页面状态才进入 Pinia。
5. 经营指标、趋势和诊断算法不得放在 Vue 组件中重复实现。
6. 不允许重新把业务实现写入 `index.html`。
7. 不要求最终用户安装 Node.js。
8. 修改前端依赖、Vite 输出目录、FastAPI SPA fallback 或 PyInstaller 静态资源路径时，必须同时验证 Release workflow。
9. 架构规则改变时必须在同一大功能提交中更新本文件和 `AGENTS.md`。
