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

更详细说明见 `docs/` 与 `AGENTS.md`。
