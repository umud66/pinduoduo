# Windows Release 发布说明

正式发布统一使用 `.github/workflows/release.yml`。

## 构建链

自 Vue 3 迁移后：

```text
解析版本并确保 Tag
  ↓
安装 Python 3.12
  ↓
安装 Node.js 22
  ↓
安装 Python 依赖
  ↓
pytest
  ↓
scripts/build_windows.ps1
  ├─ frontend npm install / npm ci
  ├─ npm run build
  ├─ 生成 app/static/
  └─ PyInstaller
  ↓
验证 Vue 与 PyInstaller 产物
  ↓
ZIP + SHA256
  ↓
创建/更新 GitHub Release
```

Node.js 只存在于构建环境，最终 Windows 用户不需要 Node/npm。

## Vue 构建要求

`frontend/vite.config.js` 输出到 `app/static/`，至少生成 `index.html` 和 `assets/*`。`app/static/` 是生成产物，PyInstaller 通过 `--add-data "app/static;app/static"` 打包。

## 常见失败

- npm install / npm run build 失败：前端依赖或 Vue 编译错误，不得跳过 Vue build。
- pytest 失败：先修测试，不允许关闭测试发布。
- PyInstaller 失败：检查构建脚本和静态资源输出。

## 维护规则

Release 构建链改变时必须同步修改本文、`AGENTS.md` 和部署文档。修改 Node/Python 版本、Vite 输出路径或 PyInstaller 静态路径后必须运行完整 Release 验证。
