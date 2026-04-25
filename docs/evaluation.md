# 评测方案

评测目标是证明 RAG 应用可持续优化，而不是只靠一次 Prompt 调试。

## 离线评测

`eval/golden_questions.json` 固定问题和期望关键词。运行：

```powershell
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4
```

生成 Markdown 报告：

```powershell
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4 --report docs\eval_report.md
```

核心指标：

- `hit_rate`：期望关键词是否被召回或出现在答案中。
- `term_coverage`：期望关键词被覆盖的比例。
- `source_count`：每个问题召回的上下文数量。
- `matched_terms`：被覆盖的关键事实。

## Prompt 迭代记录

每次调整需要记录：

- 模型名称、温度、TopK、切片大小和切片重叠。
- Prompt 版本和变更原因。
- 命中率、人工评分、错误案例。
- 是否引入新的工具调用或知识源。

## 线上 A/B

上线后可以把用户随机分流到不同 Prompt 或检索参数组，比较：

- 用户点赞率和追问率。
- 平均响应延迟。
- Token 成本。
- 工具调用成功率。
- 人工复核不通过比例。
