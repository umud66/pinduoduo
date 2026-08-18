# AGENTS.md

## 项目目标

构建面向普通拼多多商家的本地 AI 运营诊断工具。

核心约束：
- SQLite 优先，不要求安装数据库服务。
- 拼多多 API 与运营报表导入并存。
- 程序负责指标计算和异常判断，LLM 负责解释和方案生成。
- AI 接入统一 Provider，支持 OpenAI Compatible 中转站。
- Git 提交必须按大功能提交，不按文件拆提交。

## 架构规则

- `services/pdd` 只处理拼多多协议、签名、权限和原始数据。
- `services/ai` 只处理模型调用。
- 诊断规则必须可测试，不能依赖模型猜测。
- 不向 AI 发送消费者姓名、电话、地址等无关敏感信息。

## 提交规范

推荐：
- feat: add PDD connector
- feat: add AI gateway
- feat: add SKU diagnosis engine

禁止：
- add xxx.py
- update xxx.md

## 部署目标

最终用户流程：下载 -> 双击 -> 浏览器打开 -> 配置 -> 使用。
不得要求普通用户安装 Docker、Redis、PostgreSQL 或 Node。