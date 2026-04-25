# 架构设计

GeoSurveyRAG 采用分层架构，目标是把测绘业务知识和空间计算能力接入 LLM 应用。

## 数据层

- `data/knowledge` 存放测绘规范、项目总结、作业指导书、接口说明等非结构化文档。
- `ingestion.py` 负责文档加载、清洗、切片和索引构建。
- `JsonVectorStore` 是便于演示的轻量向量库，生产环境可替换为 Milvus、FAISS、Qdrant 或 Elasticsearch。

## 编排层

- `RagPipeline` 完成检索、上下文拼接、Prompt 约束和答案生成。
- `GeoAgent` 根据问题意图路由到测绘工具，例如距离量测、面积计算、WKT 边界框解析。
- `LocalLLM` 用于离线演示；真实上线可替换 OpenAI、DeepSeek、Qwen、GLM 等服务。

## 服务层

- FastAPI 提供 `/chat`、`/tool/distance`、`/tool/area`、`/tool/transform`、`/tool/wkt-bbox`。
- Dockerfile 固化运行环境，便于部署到云服务器、内网 GPU 机器或容器平台。
- 健康检查接口 `/health` 可接入 Prometheus、Nginx、Kubernetes 或企业运维平台。

## 生产化增强

- 增加异步任务队列处理大批量文档入库。
- 接入对象存储保存原始影像、DOM、DSM、点云和质量报告。
- 使用 PostGIS 实现空间查询，使用 GeoServer/ArcGIS REST 暴露图层服务。
- 对高风险回答增加人工审核和权限控制。
