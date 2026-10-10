# 评测方案

评测目标是证明 RAG 应用可持续优化，而不是只靠一次 Prompt 调试。

## 离线评测

`eval/golden_questions.json` 包含 36 条问题的期望关键词及相关来源文件名，并增加 4 条无证据样本。评测强制使用本地摘录，不调用外部大模型。运行：

```powershell
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4
```

生成 Markdown 报告：

```powershell
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4 --report docs\eval_report.md
```

核心指标：

- `source_hit_rate`：有来源标注的问题中，前 K 个片段是否命中标注文件（Hit@K）。
- `mrr`：第一个相关来源排名的倒数均值，未命中计零。
- `hit_rate`：所有样本中，召回片段包含至少一个期望关键词的比例；无证据样本计零，保留该字段便于旧脚本使用。
- `term_coverage`：检索片段覆盖期望关键词的比例。
- `answer_term_coverage`：离线摘录回答覆盖期望关键词的比例，排除原问题回显。
- `no_evidence_rate`：无证据样本得到空召回的比例。
- `source_count`：每个问题召回的上下文数量。
- `matched_terms`：检索片段中被覆盖的关键词，不等同于回答事实正确。

索引、评测样本和配置随仓库提供，结果可以复现。演示知识库较小，标注由人工编写；这些数据适合回归检查，不代表真实业务泛化能力。事实正确率和大模型忠实度需要独立人工评审。

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
