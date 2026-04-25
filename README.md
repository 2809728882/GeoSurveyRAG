# GeoSurveyRAG

面向测绘工程与 WebGIS 场景的 RAG + Agent 智能问答项目。

GeoSurveyRAG 将测绘知识库、向量检索、空间工具调用、爬虫/手动入库、离线评测和 WebGIS 前端整合成一个可部署的 FastAPI 应用。项目示例覆盖无人机航测、GNSS、地籍测量、坐标转换、遥感/LiDAR、RTK 外业和测绘成果质检等典型业务场景。

## 作者状态

作者目前正在求职，方向包括 **LLM 应用工程师、AI 应用开发、RAG/Agent 工程、WebGIS 开发、测绘/GIS 数据工程** 等。

- 联系方式：15392993401
- 微信：15392993401

## 项目亮点

- **测绘知识库 RAG**：支持 Markdown/TXT 文档入库、切片、索引、检索、上下文拼接和来源追踪。
- **向量后端可切换**：默认使用轻量 JSON 索引，便于本地运行；可切换到 FAISS，后续也可扩展 Milvus/Qdrant。
- **Agent 工具调用**：内置距离量测、闭合多边形面积计算、坐标转换、WKT 边界框解析等空间工具。
- **双通道知识入库**：支持手动录入项目经验和质检规则，也支持管理爬虫来源并同步公开网页。
- **WebGIS 前端**：提供地图画点、距离/面积计算、知识库问答、索引状态查看和知识入库入口。
- **评测闭环**：内置 36 条测绘领域 golden questions，可生成 Markdown 评测报告。
- **工程化部署**：提供 FastAPI 服务、Docker、Docker Compose、健康检查、环境变量配置和 CI workflow。

## 目录结构

```text
GeoSurveyRAG/
  src/geosurvey_rag/        # 应用核心代码
  data/knowledge/           # 示例测绘知识库
  data/sources/             # 爬虫来源配置
  eval/                     # golden questions 评测集
  docs/                     # 架构、入库、评测、向量后端文档
  examples/                 # CLI 示例
  tests/                    # 单元测试
  web/                      # FastAPI 托管的前端页面
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

浏览器打开：

```text
http://127.0.0.1:8000
```

问答接口示例：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"无人机航测成果入库前需要检查哪些质量项？\"}"
```

空间工具示例：

```bash
curl -X POST http://127.0.0.1:8000/tool/distance \
  -H "Content-Type: application/json" \
  -d "{\"points\":[[111.30,30.70],[111.32,30.72]],\"unit\":\"m\"}"
```

## 大模型 API 配置

项目默认使用 `local` 本地回答器，便于无 API Key 的情况下演示完整 RAG 链路。如果需要接入真实大模型，可使用 OpenAI-compatible 接口。

复制环境变量模板：

```powershell
copy .env.example .env
```

编辑 `.env`：

```env
LLM_PROVIDER=openai-compatible
OPENAI_API_KEY=你的_API_Key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT=60
OPENAI_TEMPERATURE=0.2
```

重新启动服务：

```powershell
uvicorn geosurvey_rag.api:app --reload --host 0.0.0.0 --port 8000
```

常见兼容接口示例：

```env
# OpenAI
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4.1-mini

# DeepSeek
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-flash

# 阿里云百炼 / DashScope OpenAI 兼容模式
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# 智谱 GLM OpenAI 兼容模式
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4-flash
```

说明：

- `OPENAI_API_KEY` 不要提交到 GitHub，仓库只保留 `.env.example`。
- 如果 API Key 缺失、网络失败或模型返回异常，系统会自动回退到本地回答器。
- 当前接口使用标准 `/chat/completions`，适合大多数 OpenAI-compatible 服务。

## 知识库入库

### 手动入库

适合录入内部项目经验、外业检查规则、质检清单、作业指导书摘要等内容。

```bash
curl -X POST http://127.0.0.1:8000/admin/knowledge/manual \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"RTK 固定解检查规则\",\"category\":\"field-survey\",\"content\":\"RTK 外业采集前应检查固定解比例、PDOP、卫星数和差分延迟。\",\"rebuild\":true}"
```

### 爬虫入库

默认爬虫来源配置在 `data/sources/crawler_sources.json`。当前预置来源包括：

- EPSG 4326 WGS84：默认启用
- EPSG 3857 Web Mercator：默认启用
- OGC GeoJSON Standard：默认关闭
- OGC API Features：默认关闭

常用命令：

```powershell
python -m geosurvey_rag.knowledge_sources list-sources
python -m geosurvey_rag.knowledge_sources add-source --name "EPSG 4490 CGCS2000" --url "https://epsg.io/4490" --tag epsg --tag cgcs2000
python -m geosurvey_rag.knowledge_sources enable-source --id ogc-geojson
python -m geosurvey_rag.knowledge_sources crawl
```

更多说明：[docs/knowledge_ingestion.md](docs/knowledge_ingestion.md)

## 索引更新

手动重建索引：

```bash
curl -X POST "http://127.0.0.1:8000/admin/index/rebuild?force=false"
```

查看索引状态：

```bash
curl http://127.0.0.1:8000/admin/index/status
```

启动自动更新器：

```powershell
python -m geosurvey_rag.index_updater --source data\knowledge --index data\index --interval 30
```

先同步爬虫来源，再检查是否需要重建索引：

```powershell
python -m geosurvey_rag.index_updater --source data\knowledge --index data\index --interval 300 --crawl-first
```

## FAISS 向量后端

默认后端是轻量 JSON 索引。如果需要使用 FAISS：

```powershell
pip install -r requirements-llm.txt
$env:VECTOR_BACKEND="faiss"
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index --backend faiss
uvicorn geosurvey_rag.api:app --reload --host 0.0.0.0 --port 8000
```

FAISS 会生成：

```text
data/index/faiss.index
data/index/faiss_chunks.jsonl
```

更多说明：[docs/vector_backends.md](docs/vector_backends.md)

## 评测

运行离线评测并生成报告：

```powershell
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4 --report docs\eval_report.md
```

当前评测集覆盖无人机航测、WebGIS、GNSS、地籍测量、坐标转换、遥感/LiDAR、RTK、全站仪、水准测量和测量数据清洗。

更多说明：[docs/evaluation.md](docs/evaluation.md)

## Docker 部署

```powershell
docker build -t geosurvey-rag:latest .
docker run --rm -p 8000:8000 geosurvey-rag:latest
```

也可以使用 Docker Compose：

```powershell
docker compose up --build
```

## 后续计划

- 接入 Milvus/Qdrant 作为分布式向量数据库后端。
- 使用 BGE、Qwen Embedding 或 OpenAI Embeddings 替换当前哈希向量。
- 接入 PostGIS、GeoServer、ArcGIS REST 或 SuperMap iServer 做真实图层查询。
- 增加鉴权、审计日志、来源级权限控制和请求链路追踪。
- 将前端升级为真实地图底图、图层叠加和空间查询界面。
