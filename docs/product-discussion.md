# 产品与技术讨论纪要

> 文档性质：技术决策记录（Design Discussion / ADR 汇总）  
> 更新时间：2026-08-18  
> 适用范围：Pinduoduo AI Operator MVP 及后续演进

本文把项目启动阶段围绕产品形态、拼多多数据能力、部署方式、SQLite、本地化、AI 网关、SKU 诊断、图片生成、Git 提交规范和 Release 自动化的讨论沉淀为可长期维护的技术文档。

本文不是逐字聊天记录，而是对已经讨论并形成共识的内容进行结构化整理。后续开发如果要偏离这些结论，应在 PR/commit 中说明原因，并同步修改本文或相关专题文档。

---

## 1. 项目起点

目标不是做一个简单的“拼多多数据查询工具”，而是做一个面向中小商家的 **本地 AI 电商运营诊断系统**。

核心价值链：

```text
拼多多 API / 商家报表
        ↓
数据标准化
        ↓
SKU 每日指标
        ↓
确定性诊断规则
        ↓
AI 解释原因与生成方案
        ↓
主图/文案/运营动作
        ↓
人工确认并执行
```

产品长期可扩展到其他电商平台，但 MVP 首先聚焦拼多多。

---

## 2. 目标用户与产品约束

目标用户主要是中小商家和非技术运营人员。

因此项目有一个高优先级非功能约束：**部署和使用门槛必须极低。**

用户最终应当只需要：

```text
下载 Windows Release
        ↓
解压
        ↓
双击 PDD运营助手.exe
        ↓
自动打开本地管理页面
        ↓
配置店铺和 AI
        ↓
开始使用
```

普通用户不应被要求安装：

- Python
- Node.js
- PostgreSQL
- MySQL
- Redis
- Docker
- Nginx
- Kubernetes

如果某项新技术会明显增加普通用户部署复杂度，应优先寻找本地替代方案。

---

## 3. 数据库决策：默认 SQLite

最初方案考虑 PostgreSQL + Redis，但结合目标用户后，确定 MVP 默认采用 SQLite。

选择 SQLite 的原因：

1. 无独立数据库安装过程。
2. 单用户/少店铺本地分析场景并发压力有限。
3. 数据文件天然方便整体备份。
4. 更适合 PyInstaller 发布。
5. 可以把用户完整数据保存在本机。

默认位置：

```text
data/app.db
```

SQLite 运行要求：

- WAL 模式。
- foreign_keys 开启。
- busy_timeout。
- 尽量短事务。
- 批量写入。
- 为 `shop/date`、`sku/date` 等高频查询建立索引。

后期如果出现几十店铺、多用户并发、超大订单量等需求，可以通过 ORM 和 migration 支持 PostgreSQL，但 PostgreSQL 不作为普通用户的默认依赖。

---

## 4. 拼多多数据能力不能做过度假设

项目讨论中最重要的技术风险之一，是“拼多多后台能看到的数据”和“开放平台应用可以通过 API 获取的数据”并不等价。

目前系统不能假定普通商家应用一定拥有以下数据权限：

- 曝光
- 点击
- 访客
- CTR
- 自然流量来源
- 推广曝光
- 推广点击
- 推广消耗
- 广告成交
- ROI

因此这些字段不得成为整个系统运行的硬前置条件。

### 4.1 当前 capability probe

当前代码中的低频只读能力探针包括：

```text
pdd.goods.list.get
pdd.order.number.list.increment.get
pdd.refund.list.increment.get
```

探针输出状态：

```text
ok

denied

error
```

其中 `denied` 应被视为权限/授权边界，而不是程序崩溃。

这些接口名称存在于当前适配和探针代码中，但是否对具体应用可用，必须以真实应用、真实店铺授权的测试结果为准。

### 4.2 API 能力分类

文档和代码中以后应把能力划分为：

- `verified`：已经用真实授权店铺成功验证。
- `adapted`：已经完成代码适配，但没有完成真实店铺验证。
- `denied`：真实授权应用确认无权限。
- `unknown`：尚未验证。

禁止因为第三方文章或历史 SDK 中存在某个接口，就直接在产品说明中标记为“已支持”。

---

## 5. 数据策略：API + 报表双通道

因为流量和推广数据存在权限不确定性，最终确定系统采用双通道：

```text
                    ┌─ 拼多多开放平台 API
数据来源 ───────────┤
                    └─ 拼多多商家后台报表 CSV/XLSX
                              ↓
                        字段识别/映射
                              ↓
                        标准化数据层
```

### API 主要承担

- 商品基础数据。
- SKU 基础数据。
- 价格。
- 库存。
- 订单。
- 订单明细。
- 售后/退款。

具体能力仍以 capability probe 为准。

### 报表主要补充

- 曝光。
- 访客。
- 点击。
- CTR。
- 转化率。
- 推广消耗。
- 推广点击。
- 推广成交。
- ROI。

导入逻辑必须允许不同版本报表出现列名变化，通过“字段别名 + 自动识别 + 用户确认映射”的方式兼容，而不是只支持某一个固定 Excel 模板。

---

## 6. 不直接分析拼多多原始 JSON

业务分析层不能长期依赖 `pdd.*` 原始 JSON。

确定的数据流：

```text
PDD Raw Response
      ↓
Pdd Adapter
      ↓
Normalize / ETL
      ↓
SQLite 标准模型
      ↓
Metric Calculator
      ↓
Diagnosis Engine
```

原因：

- 平台字段可能变化。
- 后续还有报表数据来源。
- 后续可能扩展其他平台。
- 诊断规则需要稳定的数据结构。

因此 `app/services/pdd/` 负责平台协议，诊断代码只依赖内部模型。

---

## 7. SKU Daily Metric 是分析核心

系统不能每次提问时再临时请求全部平台数据。

核心聚合应围绕 SKU 日指标建立，例如：

```text
date
shop_id
product_id
sku_id

impression
visitor
click

order_count
sales_qty
gmv

refund_count
refund_amount

ad_cost
ad_click
ad_order
ad_gmv

price
stock

ctr
cvr
refund_rate
roi
profit
profit_rate
```

字段允许为空。

特别规则：

> 缺少曝光不是曝光 = 0；缺少点击不是点击 = 0。

系统必须保留 `unknown / None` 语义，否则诊断结果会严重失真。

---

## 8. 诊断逻辑不能完全交给大模型

一个明确结论是：**LLM 不负责判断基础数学事实。**

错误方案：

```text
把 30 天 CSV 全部丢给模型
        ↓
让模型自己找异常
```

确定方案：

```text
指标计算
   ↓
规则判断
   ↓
异常分类
   ↓
Diagnosis JSON
   ↓
LLM 解释和生成策略
```

程序负责：

- 同比/环比。
- 7 日基线。
- 样本量判断。
- 阈值判断。
- 健康分。
- 严重程度。
- 问题分类。

LLM 负责：

- 用运营语言解释问题。
- 推导可能原因。
- 给出优先级明确的优化建议。
- 形成实验方案。
- 生成文案/图片 Prompt。

---

## 9. 主要 SKU 诊断类型

初始诊断体系确定为以下方向：

1. 流量问题。
2. 点击问题。
3. 转化问题。
4. 价格问题。
5. SKU 结构问题。
6. 库存问题。
7. 售后/退款问题。
8. 推广投产问题。
9. 商品生命周期衰退。

示例：

```text
曝光基本正常
CTR 下降 40%
CVR 基本正常
```

系统应优先判断：

```text
问题阶段：点击
```

而不是笼统输出：

```text
建议优化商品
```

优化建议必须尽量变成执行动作，例如：

```text
P0：保留当前主图为对照组
P1：生成突出低价的新主图
P1：生成突出核心卖点的新主图
P1：生成使用场景新主图
3 天后比较 CTR
```

---

## 10. AI Gateway 决策

AI 层不得和业务逻辑绑定具体厂商。

统一抽象：

```text
AIService.chat()
AIService.vision()
AIService.generate_image()
```

Provider 至少考虑：

- OpenAI Compatible。
- Anthropic Compatible / Claude。
- Gemini。
- 自定义中转站。

其中 OpenAI-Compatible 很重要，因为很多中转站、自建网关、国内模型聚合平台都可以通过这种协议接入。

后台配置概念：

```text
Provider Name
API Type
Base URL
API Key
Model
Vision capability
Image capability
```

API Key 必须加密存储，接口返回时不得回传完整密钥。

---

## 11. AI 输出必须结构化

诊断场景不应只保存一段不可机器处理的 Markdown。

推荐输出：

```json
{
  "summary": "该 SKU 当前主要问题为转化下降",
  "severity": "high",
  "possible_causes": [
    {
      "cause": "价格竞争力下降",
      "confidence": 0.72
    }
  ],
  "actions": [
    {
      "action": "创建价格 A/B 测试",
      "priority": 1
    }
  ]
}
```

后续前端可以直接渲染：

- 结论。
- 原因。
- 置信度。
- 建议。
- 优先级。

---

## 12. AI 图片能力

图片能力不是孤立的“文生图页面”，而应和诊断闭环结合。

典型流程：

```text
CTR 异常
  ↓
系统判断点击阶段存在问题
  ↓
分析当前主图
  ↓
生成多套主图方向
  ↓
运营人员选择并生成
  ↓
上线测试
  ↓
后续重新比较 CTR
```

图片模块长期需要支持：

- 白底图。
- 场景图。
- 卖点图。
- 主图 A/B 版本。
- 背景替换。
- 图片问题分析。
- Prompt 记录。

每次生成应记录：

- Shop。
- Product。
- SKU。
- 原图。
- Prompt。
- Provider。
- Model。
- 生成时间。

---

## 13. 本地敏感数据处理

订单数据可能包含消费者敏感信息。

明确约束：

- 姓名不发送给 LLM。
- 电话不发送给 LLM。
- 收货地址不发送给 LLM。
- Access Token 不输出到日志。
- Client Secret 不输出到日志。
- AI API Key 不输出到日志。

SKU 分析正常只需要商品、销售、退款、价格、库存和流量指标，不需要消费者身份信息。

---

## 14. 本地部署架构

MVP 不采用 Redis/Celery 等外部服务。

建议结构：

```text
PDD运营助手.exe
       ↓
FastAPI local server
       ↓
┌──────────────┬───────────────┬─────────────┐
│ PDD Adapter  │ AI Gateway    │ Importer    │
└──────────────┴───────────────┴─────────────┘
       ↓
SQLite
```

后台任务初期可以使用：

- 进程内任务。
- SQLite 任务表。
- APScheduler 或类似轻量调度。

只有在实际规模证明不够时才升级架构。

---

## 15. Windows 发布方式

项目最终面向非技术用户，因此正式包通过 GitHub Actions 在 Windows Runner 上统一构建。

发布流程：

```text
vMAJOR.MINOR.PATCH tag
        ↓
GitHub Actions
        ↓
pytest
        ↓
PyInstaller
        ↓
ZIP
        ↓
SHA256
        ↓
GitHub Release
```

支持：

- Tag 自动发布。
- Actions 手动输入版本号发布。
- Pre-release，例如 `v0.1.0-beta.1`。

正式 Release 产物不应由开发者本地随意打包后手工上传。

---

## 16. Git 提交粒度

用户明确要求：**按大功能提交，不按文件提交。**

正确：

```text
feat: add PDD connector and capability probe
feat: add AI gateway and model providers
feat: add SKU diagnosis engine
ci: publish Windows releases with GitHub Actions
docs: add product design and functional specification
```

错误：

```text
add api.py
add model.py
update README
add test.py
```

一个完整功能同时修改 API、service、model、test、docs 时，应放到同一个 commit。

---

## 17. MVP 开发顺序

讨论后确定的优先级：

### Phase 1：真实数据链路

- 店铺配置。
- PDD capability probe。
- 商品/SKU 同步。
- 订单同步。
- 售后同步。
- SQLite 标准化模型。

### Phase 2：经营数据

- 报表导入。
- 字段映射。
- SKU Daily Metric。
- 趋势和基线计算。

### Phase 3：诊断

- 确定性规则。
- 健康分。
- 严重程度。
- SKU 问题列表。

### Phase 4：AI

- Provider 管理。
- 中转站。
- 结构化诊断解释。
- AI 运营助手。

### Phase 5：图片

- Vision 分析。
- 图片 Prompt。
- 主图生成。
- A/B 素材工作流。

### Phase 6：闭环

- 创建优化任务。
- 记录执行时间。
- 重新计算指标。
- 比较优化前后效果。

---

## 18. 当前技术风险

### 18.1 拼多多权限

这是首要风险。

真实应用审批、店铺授权 scope 和平台安全规则最终决定能够自动同步的字段。

处理策略：

- capability probe。
- PDD Adapter 独立。
- API + 报表双通道。

### 18.2 报表格式变化

处理策略：

- 列别名。
- 自动识别。
- 导入预览。
- 映射模板版本化。

### 18.3 AI 幻觉

处理策略：

- 所有数值由程序计算。
- 使用结构化 Context。
- 模型不得补全缺失指标。
- AI 只做解释与策略。

### 18.4 SQLite 规模

MVP 足够，但需要持续关注：

- 数据量。
- 索引。
- WAL 文件。
- 备份。
- migration。

---

## 19. 仍需真实验证的问题

以下内容不能仅靠设计文档结案：

1. 真实拼多多应用能否调用商品列表。
2. 商品详情能获取哪些 SKU 字段。
3. 订单增量的真实返回结构和分页边界。
4. 售后增量权限。
5. 是否存在当前应用可申请的流量相关 scope。
6. 是否存在当前应用可申请的推广数据 scope。
7. 授权 Token 的刷新、失效和重新授权流程。
8. 敏感订单数据相关平台安全要求。

这些结果验证后，要更新接口能力矩阵。

---

## 20. 产品定位总结

项目长期不应被定位成：

> 拼多多 API 数据查看器

而应定位成：

> **面向中小电商商家的本地 AI 运营诊断与优化工具。**

真正长期积累的产品资产包括：

1. 电商经营指标体系。
2. SKU Diagnosis Engine。
3. Optimization Knowledge Base。
4. 数据标准化能力。
5. 优化实验闭环。

模型厂商和平台 API 都可以替换，而这些能力应当沉淀在项目内部。
