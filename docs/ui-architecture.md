# 前端 UI 架构

## 原则

前端虽然不引入 Node 构建链，但必须按功能模块组织，不允许继续把页面、API、状态、格式化、组件和业务逻辑全部堆在一个 `app.js` 或一个 CSS 文件中。

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
    │   └── sku-drawer.js
    └── pages/
        ├── dashboard.js
        ├── skus.js
        ├── data.js
        ├── studio.js
        └── settings.js
```

## 模块职责

- `core/`：无业务状态的基础能力。
- `state.js`：跨页面共享的店铺、Provider 和当前页面状态。
- `components/`：可复用 UI 组件及其交互。
- `pages/`：每个主页面一个独立模块，页面内部复杂功能可以继续拆子模块。
- `app.js`：只负责启动、路由和页面编排，不承载具体业务实现。
- CSS 按基础、布局、组件和页面样式分层。

## 约束

1. 新增主页面必须新建 `pages/<feature>.js`，禁止把实现直接写进 `app.js`。
2. 同一个页面超过约 500 行或包含多个独立工作区时，应继续拆成页面子模块或组件。
3. 通用 HTTP、Toast、格式化、加载状态不得在各页面重复实现。
4. 页面之间通过 `state.js` 和显式参数协作，不使用散落的全局变量。
5. 不引入前端打包工具作为普通用户运行依赖；浏览器使用原生 ES Modules。
6. PyInstaller 必须继续递归打包整个 `app/static/`。

## 当前数据中心

`pages/data.js` 负责拼多多同步中心、能力探针和报表导入。后续如果该文件继续增长，应优先拆成：

```text
pages/data/
├── sync-center.js
├── capability-probe.js
└── report-import.js
```

而不是再次形成新的单体文件。
