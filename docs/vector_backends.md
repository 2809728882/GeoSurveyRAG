# 向量数据库后端

GeoSurveyRAG 当前支持两种索引模式：

## JSON 轻量索引

默认模式，适合离线演示、面试讲解和无依赖运行。

```powershell
$env:VECTOR_BACKEND="json"
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index --backend json
```

特点：

- 不依赖第三方向量库。
- 使用中文 n-gram + 稀疏余弦相似度。
- 适合小知识库和快速原型。

## FAISS 本地向量索引

适合展示向量数据库和 RAG 工程化能力。

```powershell
pip install -r requirements-llm.txt
$env:VECTOR_BACKEND="faiss"
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index --backend faiss
```

生成文件：

- `data/index/faiss.index`
- `data/index/faiss_chunks.jsonl`

当前使用稳定哈希向量作为离线 Embedding 占位。生产环境建议替换为：

- `bge-small-zh-v1.5`
- `bge-m3`
- `text-embedding-3-small`
- `Qwen3-Embedding`

## Milvus 接入路线

Milvus 更适合多知识库、多租户和大规模向量检索。建议新增 `MilvusVectorStore`，保持与当前 `add/save/load/search` 接口一致。

推荐集合字段：

- `chunk_id`: VarChar，主键。
- `source`: VarChar，文档来源。
- `text`: VarChar，文本片段。
- `embedding`: FloatVector，向量字段。
- `metadata`: JSON，业务元数据。

检索策略：

- 使用 `COSINE` 或 `IP` 相似度。
- 结合 `source`、`project_id`、`doc_type` 做过滤。
- 对测绘规范、项目资料、质检报告分别建 collection 或 partition。

这样可以把本项目从单机 FAISS 平滑升级到企业级 Milvus，而不改动 FastAPI、Agent 和评测层。
