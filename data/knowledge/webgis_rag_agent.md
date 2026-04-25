# WebGIS 与 RAG Agent 集成方案

WebGIS 智能问答系统可以把地图服务、空间数据库、业务 API 和大语言模型结合起来。

推荐架构如下：

- 前端使用 Vue、React 或 OpenLayers/Cesium 展示地图、图层、查询结果和问答面板。
- 后端使用 FastAPI 提供统一服务，封装 RAG 检索、工具调用、用户权限和日志审计。
- 知识库接入测绘规范、项目文档、元数据说明、接口文档和历史工单。
- 向量数据库可选 FAISS、Milvus、Qdrant 或 Elasticsearch dense vector。
- Agent 工具可包括距离量测、面积计算、坐标转换、缓冲区分析、空间相交、图层查询和 ArcGIS REST 调用。
- Prompt 需要约束回答边界，要求模型引用来源、说明坐标系统、暴露不确定性，并在缺少数据时提出补充项。

上线后应监控接口延迟、召回命中率、Token 成本、用户反馈、工具调用成功率和高风险回答比例。
