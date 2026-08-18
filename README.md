# Pinduoduo AI Operator

面向拼多多中小商家的本地化 AI 运营诊断工具。项目目标是 **低门槛、一键启动、本地 SQLite 存储、可接拼多多开放平台、兼容各类 OpenAI 格式大模型/中转站，并支持图片生成**。

> 当前处于 MVP 开发阶段。拼多多开放平台的实际接口权限以你的应用审核结果和店铺授权 scope 为准。系统因此采用“API 自动同步 + 商家报表导入”的双通道设计，不把曝光、点击、推广等指标硬编码为必然可通过 API 获取。

## 目标体验

最终普通用户只需要：

1. 下载 Windows 发布包。
2. 双击 `PDD运营助手.exe`。
3. 在浏览器自动打开本地管理界面。
4. 填写拼多多应用授权信息。
5. 填写 AI 服务地址、Key 和模型名。
6. 开始同步和诊断。

不要求安装 PostgreSQL、Redis、Docker、Node.js，也不要求用户理解数据库。

## 技术路线

- Python 3.11+
- FastAPI：本地 HTTP 服务与 API
- SQLite + SQLAlchemy：本地持久化
- httpx：拼多多与 AI HTTP 调用
- openpyxl：运营报表导入
- cryptography：本地密钥加密
- PyInstaller：Windows 单文件/目录发布
- 原生 HTML/CSS/JS：避免生产环境依赖 Node.js

## 数据目录

运行时数据默认写入：

```text
data/
├── app.db
├── secret.key
├── imports/
├── images/
└── backups/
```

该目录应当定期备份。删除程序时不要直接删除 `data/`，否则会同时删除店铺历史数据。

## 开发启动

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python scripts/dev.py
```

打开 `http://127.0.0.1:8765`。

## 设计原则

- 数据先标准化，再做诊断，最后交给 LLM 解释。
- 数学判断和异常规则由程序完成，不让模型“猜数据”。
- API 权限不确定的数据必须提供报表导入补充路径。
- 用户敏感订单信息默认不发送给任何 AI 服务。
- 模型层统一走 Provider/Gateway，不在业务代码里绑定单一厂商。
- 提交以“大功能”为单位，禁止按单文件机械拆 commit。

## 文档

项目设计和产品功能以仓库文档为准：

- [`docs/product-discussion.md`](docs/product-discussion.md)：项目启动阶段的产品与技术讨论纪要，记录关键架构决策、约束、风险和演进方向。
- [`docs/functional-spec.md`](docs/functional-spec.md)：详细功能说明书，描述模块、流程、数据、验收标准和版本路线。
- [`docs/diagnosis-engine.md`](docs/diagnosis-engine.md)：SKU 诊断引擎、GMV 拆解、影响度、置信度、优先级和验证动作设计。
- [`docs/pdd-sync.md`](docs/pdd-sync.md)：拼多多商品、订单、售后同步策略及恢复机制。
- [`docs/ui-architecture.md`](docs/ui-architecture.md)：前端模块化结构与约束。
- [`docs/architecture.md`](docs/architecture.md)：系统总体架构。
- [`docs/deployment.md`](docs/deployment.md)：本地部署原则。
- [`docs/release.md`](docs/release.md)：Windows Release 发布流程。
- [`AGENTS.md`](AGENTS.md)：所有后续编码 Agent 必须遵循的工程约束。

其中 `product-discussion.md` 用于保存“为什么这样设计”，`functional-spec.md` 用于定义“系统最终应该做什么”。功能或架构发生实质变化时应同步更新对应文档。

## Release 发布

正式 Windows 包由 GitHub Actions 自动构建。推送 `v0.1.0` 形式的 Tag 后，`Release Windows` 工作流会运行测试、执行 PyInstaller 打包，并创建 GitHub Release，上传 Windows x64 ZIP 和 SHA256 校验文件。

也可以从 GitHub Actions 页面手动运行 `Release Windows`，输入版本 Tag 发布。
