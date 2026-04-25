# GeoSurveyRAG

面向测绘工程与 WebGIS 场景的开源 LLM 应用示例：把测绘规范、项目文档、外业记录和空间工具封装成一个可部署的 RAG + Agent 问答服务。

这个项目适合放在简历里对应「LLM 应用工程师」岗位：它覆盖 RAG、Agent 工具调用、Prompt 编排、Embedding/向量检索、评测、FastAPI 服务化、Docker 部署和工程文档，同时和测绘工程专业背景直接相关。

## 项目亮点

- **测绘知识库 RAG**：支持 Markdown/TXT 文档切片、轻量向量化、相似度召回、上下文拼接与答案生成。
- **WebGIS/测绘工具调用**：内置距离量测、闭合多边形面积、WKT 边界框、经纬度/投影坐标转换接口。
- **可切换向量后端**：默认 JSON 轻量索引便于离线演示，可切换 FAISS 展示向量数据库工程化能力。
- **WebGIS 前端页面**：内置地图画点、距离/面积计算、知识库问答和索引状态查看。
- **Agent 编排思路**：根据问题自动判断是否调用空间工具，再结合知识库生成可追溯回答。
- **模型可替换**：默认提供本地规则型回答器，便于离线演示；预留 OpenAI/国产大模型 API 接入位。
- **质量闭环**：提供评测集、离线评测脚本和指标输出，可扩展到 A/B 测试。
- **上线友好**：FastAPI + Docker + 健康检查 + 配置化环境变量，适合展示完整交付能力。

## 目录结构

```text
GeoSurveyRAG/
  src/geosurvey_rag/        # 核心应用代码
  data/knowledge/           # 示例测绘知识库
  eval/                     # 评测集
  tests/                    # 单元测试
  docs/                     # 架构与评测文档
  examples/                 # CLI 演示
```

## 快速开始

```powershell
cd D:\github\GeoSurveyRAG
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index
uvicorn geosurvey_rag.api:app --reload --host 0.0.0.0 --port 8000
```

打开浏览器访问：

```text
http://127.0.0.1:8000
```

访问接口：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"无人机航测成果入库前需要检查哪些质量项？\"}"
```

工具调用示例：

```bash
curl -X POST http://127.0.0.1:8000/tool/distance \
  -H "Content-Type: application/json" \
  -d "{\"points\":[[111.30,30.70],[111.32,30.72]],\"unit\":\"m\"}"
```

## Docker 部署

```powershell
docker build -t geosurvey-rag:latest .
docker run --rm -p 8000:8000 geosurvey-rag:latest
```

## 知识库自动更新

项目会为索引生成 `data/index/manifest.json`，记录文档哈希、更新时间和切片数量。新增、删除或修改 `data/knowledge` 下的文档后，可手动触发重建：

```bash
curl -X POST "http://127.0.0.1:8000/admin/index/rebuild?force=false"
```

查看索引状态：

```bash
curl http://127.0.0.1:8000/admin/index/status
```

也可以启动轮询式自动更新进程：

```powershell
python -m geosurvey_rag.index_updater --source data\knowledge --index data\index --interval 30
```

生产环境可把该命令放入独立容器、Windows 计划任务、Linux systemd timer 或 CI/CD 流水线。

## 手动入库与爬虫入库

知识库支持两种来源：

- `manual`：录入内部测绘项目经验、质检规则、作业指导书摘要。
- `crawler`：从配置 URL 同步公开网页和接口文档，支持默认来源、手动添加、启停和删除来源。

详见：[docs/knowledge_ingestion.md](docs/knowledge_ingestion.md)

## FAISS 向量后端

默认使用轻量 JSON 索引，适合无依赖演示。需要展示向量数据库工程化时，可安装可选依赖并切换后端：

```powershell
pip install -r requirements-llm.txt
$env:VECTOR_BACKEND="faiss"
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index --backend faiss
uvicorn geosurvey_rag.api:app --reload --host 0.0.0.0 --port 8000
```

FAISS 会生成 `data/index/faiss.index` 和 `data/index/faiss_chunks.jsonl`。后续可以把该接口替换为 Milvus/Qdrant，RAG 层不需要大改。

## 评测报告

当前评测集覆盖无人机航测、WebGIS、GNSS、地籍测量、坐标转换、遥感/LiDAR 和外业仪器。

```powershell
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4 --report docs\eval_report.md
```

## 简历写法

**GeoSurveyRAG：面向测绘知识库的 RAG + Agent 智能问答平台**

- 基于 FastAPI 设计 LLM 应用服务，完成文档切片、Embedding、向量召回、Prompt 组装、答案生成与来源追踪的端到端 RAG 流程。
- 结合测绘工程场景封装距离量测、面积计算、坐标转换、WKT 解析等工具调用能力，实现“知识问答 + 空间计算”的 Agent 编排。
- 构建 30+ 条测绘问答评测集与命中率/关键词覆盖率指标，支持对 Prompt、切片大小、TopK、向量后端等参数进行迭代优化。
- 使用 Docker 完成服务化部署，输出架构文档、接口文档与工程规范，沉淀可复用的 AI+WebGIS 项目模板。

## 后续可增强方向

- 接入 Milvus/FAISS/Qdrant，替换当前轻量 JSON 向量索引。
- 接入 LangChain 或 LlamaIndex 的 Retriever、Tool、AgentExecutor。
- 接入 Dify/Coze 工作流，把本项目作为测绘业务插件服务。
- 增加 PostGIS、GeoServer、SuperMap/iServer、ArcGIS REST 的业务接口适配。
- 使用 LoRA/QLoRA 对测绘问答小模型做参数高效微调实验。
