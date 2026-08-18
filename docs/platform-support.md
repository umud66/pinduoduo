# 多平台支持与发布矩阵

> 更新时间：2026-08-18  
> 状态：Release 基线

项目正式发布从 Windows-only 扩展为 Windows、macOS、Linux 多平台。前端仍由 Vue/Vite 构建，后端仍由 FastAPI + SQLite 提供本地服务；各平台必须在对应原生 GitHub-hosted runner 上使用 PyInstaller 构建，禁止在单一系统上交叉伪造其他平台产物。

## 1. 首批正式构建矩阵

| 平台 | 架构 | GitHub Runner | Release 资产 |
|---|---|---|---|
| Windows | x64 | `windows-2025` | `PDD-AI-Operator-vX.Y.Z-windows-x64.zip` |
| Linux | x64 | `ubuntu-24.04` | `PDD-AI-Operator-vX.Y.Z-linux-x64.tar.gz` |
| macOS | Apple Silicon / arm64 | `macos-15` | `PDD-AI-Operator-vX.Y.Z-macos-arm64.zip` |
| macOS | Intel / x64 | `macos-15-intel` | `PDD-AI-Operator-vX.Y.Z-macos-x64.zip` |

Windows ARM64 与 Linux ARM64 暂不作为首批稳定资产；新增架构前必须确认 GitHub runner 稳定性、Python/PyInstaller 依赖兼容性并补充实际构建验证。

## 2. 平台产物形态

### Windows

PyInstaller `onedir`，用户解压后运行：

```text
PDD运营助手.exe
```

### macOS

PyInstaller `onedir + --windowed`，生成：

```text
PDD运营助手.app
```

Apple Silicon 与 Intel 分开构建，不制作未经验证的 Universal2 合并包。

当前 CI 未配置 Apple Developer ID 签名和 notarization。正式面向大量普通 Mac 用户分发前，应增加签名、公证与对应 Secrets 管理；在此之前 Release 文档必须明确这一限制。

### Linux

PyInstaller `onedir`，压缩包内包含：

```text
PDD-AI-Operator/
└── PDD-AI-Operator
```

首批以 Ubuntu x64 runner 构建。Linux 二进制兼容范围受 glibc 与系统库影响，发布说明不得宣称兼容所有发行版；后续根据真实用户环境补充测试矩阵。

## 3. 运行数据目录

开发环境仍使用仓库根目录：

```text
data/
```

冻结后的 Release 不能依赖当前工作目录。

### Windows

保持便携模式：

```text
<exe 所在目录>/data/
```

这样现有 Windows 用户升级时仍可保留原数据目录。

### macOS

使用：

```text
~/Library/Application Support/PDD AI Operator/
```

避免 Finder 启动 `.app` 时因工作目录不确定导致数据库写入错误。

### Linux

遵守 XDG 约定：

```text
$XDG_DATA_HOME/pdd-ai-operator/
```

如果没有 `XDG_DATA_HOME`：

```text
~/.local/share/pdd-ai-operator/
```

所有平台都允许通过：

```text
PDD_AI_DATA_DIR
```

显式覆盖数据目录。

## 4. Release 工作流原则

`.github/workflows/release.yml` 必须分为：

```text
prepare
  ↓
quality
  ↓
build matrix
  ├─ Windows x64
  ├─ Linux x64
  ├─ macOS arm64
  └─ macOS x64
  ↓
publish
```

要求：

- `quality` 至少运行 Python 测试和 Vue build。
- 每个平台在原生 runner 上重新安装依赖并执行 PyInstaller。
- 每个平台生成独立 SHA256。
- `publish` 汇总全部平台资产后只创建/更新一次 GitHub Release。
- Release 额外生成 `SHA256SUMS.txt`。
- 任意稳定平台构建失败时，不发布不完整的正式 Release。

## 5. 构建脚本职责

- `scripts/build_windows.ps1`：Windows Vue + PyInstaller 构建。
- `scripts/build_unix.sh`：Linux/macOS Vue + PyInstaller 构建。
- macOS 分支必须生成 `.app`。
- Linux 分支必须生成可执行的 onedir bundle。
- 构建脚本不得要求最终用户安装 Node.js 或 Python。

## 6. 验收标准

每次修改跨平台构建、运行路径、依赖或静态资源布局时至少验证：

1. Workflow YAML 可解析。
2. Python `compileall` / pytest。
3. Vue build。
4. Windows PyInstaller。
5. Linux PyInstaller。
6. macOS arm64 PyInstaller。
7. macOS Intel PyInstaller。
8. 四类资产均被 `publish` job 收集。
9. SHA256 文件完整。
10. 各平台启动后能够创建数据库、打开浏览器并访问 Vue 页面。

如果当前开发环境无法完成某个平台原生构建，只能将该验证交给 GitHub Actions，并必须明确记录“未在本地验证”，不得声称通过。
