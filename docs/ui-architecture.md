# 前端 UI 架构

## 原则

前端虽然不引入 Node 构建链，但必须按功能模块组织，不允许把页面、API、状态、格式化、组件和业务逻辑全部堆在一个 `app.js` 或一个 CSS 文件中。

## 目录

```text
app/static/
├── index.html
├── css/
│   ├── base.css
│   ├── layout.css
│   ├── components.css
│   └── pages.css
└── js/
    ├── app.js
    ├── state.js
    ├── onboarding.js
    ├── core/
    │   ├── api.js
    │   ├── dom.js
    │   └── format.js
    ├── components/
    │   ├── shell.js
    │   ├── sku-drawer.js
    │   └── sync-watch.js
    └── pages/
        ├── dashboard.js
        ├── skus.js
        ├── studio.js
        ├── settings.js
        └── data/
            ├── index.js
            ├── sync-center.js
            ├── capability-probe.js
            ├── report-import.js
            └── demo-data.js
```

## 模块职责

- `core/`：无业务状态的 HTTP、DOM、格式化等基础能力。
- `state.js`：跨页面共享的店铺、Provider 和当前页面状态。
- `components/`：可复用 UI 组件及跨页面行为，例如 SKU 抽屉和全局同步监听。
- `pages/`：每个主页面一个独立模块；复杂页面继续使用子目录拆分。
- `pages/data/`：数据中心已按同步、能力检测、报表导入和演示数据拆分，`index.js` 只做页面组装。
- `app.js`：只负责启动、路由、页面编排和跨页面数据更新事件，不承载具体业务实现。
- CSS 按基础、布局、组件和页面样式分层。

## 约束

1. 新增主页面必须新建 `pages/<feature>.js`，禁止把实现直接写进 `app.js`。
2. 同一个页面包含两个以上可独立测试/维护的工作区时，优先直接建立 `pages/<feature>/` 子目录，而不是等到单文件超过千行再拆。
3. 通用 HTTP、Toast、格式化、加载状态不得在各页面重复实现。
4. 页面之间通过 `state.js`、显式参数和浏览器自定义事件协作，不使用散落的全局变量。
5. 不引入前端打包工具作为普通用户运行依赖；浏览器使用原生 ES Modules。
6. PyInstaller 必须继续递归打包整个 `app/static/`。
7. 后台任务状态属于跨页面信息时，应放在独立组件中监听，不得由 Dashboard、SKU 页各自重复实现轮询。

## 数据更新事件

当前统一使用 `pdd:data-updated` 事件通知经营数据发生变化。来源包括同步完成、报表导入和演示数据创建。应用入口根据当前页面决定是否刷新 Dashboard/SKU 数据，避免功能模块相互直接调用。
