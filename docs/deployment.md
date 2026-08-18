# 部署与发布

## 普通用户目标

正式 Release 支持 Windows、macOS 和 Linux。普通用户运行发布包时不需要安装 Python、Node.js/npm、PostgreSQL、Redis 或 Docker。

### Windows

下载 `windows-x64.zip`，解压后双击：

```text
PDD运营助手.exe
```

### macOS

按芯片选择：

```text
macos-arm64.zip   Apple Silicon
macos-x64.zip     Intel
```

解压后运行 `PDD运营助手.app`。

当前 CI 尚未配置 Apple Developer ID 签名/notarization，macOS 可能显示安全警告。此状态属于发布限制，不能在文档中隐藏。

### Linux

下载 `linux-x64.tar.gz`，解压后运行：

```text
PDD-AI-Operator/PDD-AI-Operator
```

Linux 首批按 Ubuntu x64 runner 构建，兼容范围需要通过真实发行版继续验证。

## 源码开发环境

源码开发需要 Python 3.11+ 和 Node.js 22+。

Windows 可使用 `start.bat`。`scripts/dev.py` 启动 FastAPI `:8765` 和 Vite `:5173`，开发浏览器入口为 `http://127.0.0.1:5173`。

## 正式前端产物

`frontend/` 是 Vue 源码，`app/static/` 是 Vite 生成产物：

```text
frontend npm run build
       ↓
app/static/index.html
app/static/assets/
       ↓
PyInstaller
```

正式包不直接维护 `app/static/` 源码。

## 平台构建脚本

Windows：

```powershell
./scripts/build_windows.ps1
```

Linux/macOS：

```bash
./scripts/build_unix.sh
```

两个脚本都负责 Vue build 后再运行 PyInstaller。

## GitHub Release

`.github/workflows/release.yml` 使用原生 Runner 矩阵构建：

```text
Windows x64
Linux x64
macOS arm64
macOS Intel x64
```

所有平台成功后由单独的 `publish` job 汇总发布，避免矩阵 job 同时创建 Release。

## 数据目录

源码开发默认：

```text
./data/
```

冻结 Release：

```text
Windows:
<exe>/data/

macOS:
~/Library/Application Support/PDD AI Operator/

Linux:
$XDG_DATA_HOME/pdd-ai-operator/
或 ~/.local/share/pdd-ai-operator/
```

可通过 `PDD_AI_DATA_DIR` 覆盖。

数据库与 `secret.key` 必须始终位于同一数据目录的备份范围中。升级时不得为了兼容新版本而要求用户删除数据库。

## 数据迁移

公开稳定版前 schema 变化必须加入 migration：

1. 启动前备份。
2. 执行版本化 migration。
3. 失败时停止启动并保留旧数据。
4. 不允许通过删除 `app.db` 解决升级。
