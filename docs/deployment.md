# 部署与发布

## 普通用户目标

正式 Windows 用户只需下载 Release、解压、双击 `PDD运营助手.exe`。普通用户不需要安装 Python、Node.js/npm、PostgreSQL、Redis、Docker。

## 源码开发环境

Vue 迁移后，源码开发需要 Python 3.11+ 和 Node.js 22+。`start.bat` 检查 Python/npm，`scripts/dev.py` 启动 FastAPI `:8765` 和 Vite `:5173`，浏览器开发入口为 `http://127.0.0.1:5173`。

## 正式前端产物

`frontend/` 是源码，`app/static/` 是 Vite build 生成产物：

```text
frontend npm run build
       ↓
app/static/index.html
app/static/assets/
```

FastAPI 生产环境托管 `/assets`，并对 Vue Router history 路由执行 SPA fallback。

## Windows 构建

`./scripts/build_windows.ps1` 统一完成 npm install/npm ci、npm run build、校验 app/static/index.html 和 PyInstaller。

## GitHub Release

workflow 在 `windows-latest` 中安装 Python 3.12 与 Node.js 22，运行 pytest，再完成 Vue + PyInstaller 构建，最后创建 ZIP/SHA256 和 GitHub Release。

## 数据与升级

运行数据仍位于 `data/`。发布包不得携带开发者自己的数据库、Key 或 Token。用户升级必须保留原 `data/`。公开稳定版前 schema 变化必须加入 migration。
