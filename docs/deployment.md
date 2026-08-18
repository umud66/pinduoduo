# 部署与发布

## 普通用户目标

正式版不让用户执行命令行。Windows 用户下载发布包后双击 `PDD运营助手.exe` 即可启动，本地浏览器自动打开 `http://127.0.0.1:8765`。

## 源码用户

Windows 可双击：

```text
start.bat
```

它会自动：

1. 创建 `.venv`。
2. 安装项目依赖。
3. 启动本地服务。
4. 自动打开浏览器。

该模式需要机器预先安装 Python，仅供开发和源码试用。

## 构建 Windows 发布包

PowerShell：

```powershell
./scripts/build_windows.ps1
```

构建产物位于：

```text
dist/PDD运营助手/
```

发布时应把程序和空的 `data/` 初始化逻辑一起测试。不要把开发者自己的 `app.db`、API Key、Access Token 打入发布包。

## 数据备份

最简单可靠的用户备份单位是整个 `data/` 目录。未来设置页应提供“一键备份”，实现方式为在无写事务时创建 SQLite 在线备份并同时复制 `secret.key`。

## 升级策略

当前 MVP 用 SQLAlchemy `create_all` 初始化数据库。进入首次公开发布前，需要加入版本化 schema migration，升级流程必须做到：

1. 启动前备份。
2. 执行 migration。
3. migration 失败则停止启动并保留原数据。
4. 不允许通过删除 `app.db` 解决升级问题。

## GitHub Release 自动发布

仓库使用 `.github/workflows/release.yml` 构建 Windows 发布包。

### 推荐方式：推送版本 Tag

```bash
git tag v0.1.0
git push origin v0.1.0
```

Action 会在 `windows-latest` 上自动：

1. 安装 Python 3.12 和项目依赖。
2. 运行完整单元测试。
3. 使用 PyInstaller 构建 `PDD运营助手`。
4. 压缩为 `PDD-AI-Operator-v0.1.0-windows-x64.zip`。
5. 生成对应 SHA256 校验文件。
6. 创建 GitHub Release，并上传 ZIP 和校验文件。

### 手动发布

也可以在 GitHub 的 **Actions -> Release Windows -> Run workflow** 中填写 `v0.1.0` 形式的 Tag。若该 Tag 尚不存在，工作流会把它创建在当前选择的提交上，然后发布 Release。

Tag 必须符合 `vMAJOR.MINOR.PATCH`，预发布版本可使用 `v0.1.0-beta.1`。包含 `-` 后缀的版本会自动标记为 prerelease。

## 用户升级与数据

发布包不内置或覆盖 `data/` 中的 SQLite 数据。用户升级时应保留原有 `data/` 目录；正式加入自动更新前，不应设计任何会在升级时删除数据库的流程。
