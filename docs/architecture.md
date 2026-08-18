# Architecture

## Local-first

```text
Browser
  |
FastAPI
  |
+-- PDD Adapter
+-- Report Import
+-- Diagnosis Engine
+-- AI Gateway
+-- SQLite
```

## Data strategy

采用双通道：

1. 拼多多授权 API 自动同步。
2. 商家后台 CSV/XLSX 报表补充曝光、点击、推广等运营指标。

不假设所有店铺都拥有全部开放平台权限。

## Diagnosis

流程：

原始数据 -> 标准化 -> 指标计算 -> 规则诊断 -> LLM解释 -> 优化建议。

数学结果不交给模型重新计算。