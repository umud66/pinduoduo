# 多平台 Release 发布说明

正式发布统一使用 `.github/workflows/release.yml`。Release 目标是一次版本发布同时生成 Windows、Linux 和两种 macOS 架构的原生产物。

## 1. 发布入口

支持：

```text
Actions -> Release Multi-platform -> Run workflow
```

手工输入可使用：

```text
1.0.0
v1.0.0
1.0.0-beta.1
v1.0.0-beta.1
```

工作流统一规范化为 `vMAJOR.MINOR.PATCH` 形式。

也可以直接推送版本 Tag。

## 2. 构建链

```text
prepare
  解析/规范化 Tag
  确保规范化 Tag 存在
        ↓
quality (Ubuntu)
  Python 3.12
  Node.js 22
  compileall
  pytest
  Vue build
        ↓
build matrix
  Windows x64       windows-2025
  Linux x64         ubuntu-24.04
  macOS arm64       macos-15
  macOS Intel x64   macos-15-intel
        ↓
每个平台
  安装 Python/Node 依赖
  Vue build
  PyInstaller 原生构建
  打包
  单独 SHA256
  upload-artifact
        ↓
publish
  下载全部平台 assets
  生成 SHA256SUMS.txt
  创建/更新一个 GitHub Release
  上传全部资产
```

Node.js 和 Python 是开发/CI 构建依赖，不是最终用户运行依赖。

## 3. Release 资产

以 `v1.0.0` 为例：

```text
PDD-AI-Operator-v1.0.0-windows-x64.zip
PDD-AI-Operator-v1.0.0-windows-x64.zip.sha256

PDD-AI-Operator-v1.0.0-linux-x64.tar.gz
PDD-AI-Operator-v1.0.0-linux-x64.tar.gz.sha256

PDD-AI-Operator-v1.0.0-macos-arm64.zip
PDD-AI-Operator-v1.0.0-macos-arm64.zip.sha256

PDD-AI-Operator-v1.0.0-macos-x64.zip
PDD-AI-Operator-v1.0.0-macos-x64.zip.sha256

SHA256SUMS.txt
```

## 4. 平台说明

### Windows

解压后运行 `PDD运营助手.exe`。

### macOS Apple Silicon

M1/M2/M3/M4 等 Apple Silicon 设备使用 `macos-arm64.zip`。压缩包内为 `PDD运营助手.app`。

### macOS Intel

Intel Mac 使用 `macos-x64.zip`。

当前没有配置 Apple Developer ID 签名/notarization，因此 macOS 可能显示系统安全警告。正式大规模分发前需要补充签名与公证流程；禁止在文档里描述为“已签名”。

### Linux

首批发布 `linux-x64.tar.gz`。解压后运行 bundle 中的 `PDD-AI-Operator`。Linux 发行版兼容性必须以实际测试为准，不宣称覆盖所有 glibc/发行版版本。

## 5. 构建失败原则

以下任一步失败都不得绕过：

- Python 测试。
- Vue build。
- 任一稳定平台 PyInstaller。
- 平台资产打包。
- SHA256 生成。

正式 Release 必须是完整矩阵。需要临时排除平台时，应使用预发布版本并在 Release Notes 中明确说明，不能静默缺包。

## 6. 维护规则

修改以下内容时必须同步检查本文件、`docs/platform-support.md`、`docs/deployment.md`、`AGENTS.md`：

- Runner label。
- Python/Node 版本。
- Vue 输出路径。
- PyInstaller 参数。
- macOS bundle 设置。
- 平台数据目录。
- Release 资产命名。
- 支持的平台/CPU 架构。

平台支持详细设计见 `docs/platform-support.md`。
