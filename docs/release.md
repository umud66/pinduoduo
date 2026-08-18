# Windows Release 发布说明

本文描述 Pinduoduo AI Operator 的 Windows 正式发布流程。正式发布统一使用 GitHub Actions，不要求维护者在本地构建后手工上传。

## 1. 发布入口

工作流：`.github/workflows/release.yml`

支持两种方式。

### 方式 A：GitHub Actions 手动发布

进入仓库：

```text
Actions -> Release Windows -> Run workflow
```

版本号可以输入：

```text
1.0.0
v1.0.0
1.0.0-beta.1
v1.0.0-beta.1
```

工作流会自动规范化为带 `v` 的 Git Tag。例如输入 `1.0.0`，最终发布 Tag 和 Release 都是 `v1.0.0`。

### 方式 B：推送 Git Tag

支持带 `v` 和不带 `v` 的 SemVer Tag：

```bash
git tag v1.0.0
git push origin v1.0.0
```

也可以推送 `1.0.0`，工作流内部仍会规范化为 `v1.0.0` 作为正式 Release Tag。为了仓库 Tag 风格统一，人工创建 Tag 时仍推荐直接使用 `v1.0.0`。

## 2. 版本格式

稳定版：

```text
1.0.0
v1.0.0
2.3.15
v2.3.15
```

预发布：

```text
1.0.0-beta.1
v1.0.0-beta.1
1.0.0-rc.2
```

非法示例：

```text
1.0
release-1.0.0
latest
```

## 3. 工作流执行顺序

```text
解析并规范化版本
  -> 确保 Release Tag 存在
  -> 安装 Python
  -> 安装项目依赖
  -> pytest
  -> PyInstaller Windows 构建
  -> ZIP 打包
  -> SHA256
  -> 创建/更新 GitHub Release
  -> 上传发布资产
```

任何测试或构建步骤失败时，不应继续创建正式发布资产。

## 4. 发布资产

以 `1.0.0` 为例：

```text
PDD-AI-Operator-v1.0.0-windows-x64.zip
PDD-AI-Operator-v1.0.0-windows-x64.zip.sha256
```

ZIP 内为 PyInstaller `onedir` 产物，普通 Windows 用户解压后直接运行 `PDD运营助手.exe`。

## 5. 常见错误

### Invalid release version

只接受 SemVer 三段版本号。`1.0.0` 和 `v1.0.0` 均有效。

### pytest 失败

属于代码测试失败，不应绕过测试发布。先修复测试。

### Build Windows application 失败

查看 `scripts/build_windows.ps1` 和 PyInstaller 输出。新增依赖、静态目录或动态导入后，需要同步调整打包配置。

### Release upload 失败

确认 Actions 的 `GITHUB_TOKEN` 具有 `contents: write` 权限，并检查同名 Release/资产是否存在。工作流使用 `--clobber` 覆盖同名资产。

## 6. 维护约束

- 发布版本最终统一为 `vMAJOR.MINOR.PATCH`。
- 手动输入可以省略 `v`，工作流负责规范化。
- 不允许通过关闭测试来解决发布失败。
- 正式 Windows Release 必须由 GitHub Actions 构建。
- 修改 Release 工作流时，应同步更新本文。
