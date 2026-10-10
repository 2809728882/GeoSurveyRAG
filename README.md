# GeoSurveyRAG

面向测绘工程与 WebGIS 场景的 RAG + Agent 智能问答项目。

GeoSurveyRAG 将测绘知识库、向量检索、空间工具调用、爬虫/手动入库、离线评测和 WebGIS 前端整合成一个可部署的 FastAPI 应用。项目示例覆盖无人机航测、GNSS、地籍测量、坐标转换、遥感/LiDAR、RTK 外业和测绘成果质检等典型业务场景。

## 0.2 更新

- **混合检索与引用**：BM25 与词频/哈希向量排序通过 RRF 融合，支持来源筛选、相似度阈值、片段编号和资料引用；无资料且无工具结果时直接提示补充资料。
- **测绘计算校验**：默认使用 WGS84 椭球测地线距离和多边形面积，校验经纬度、单位、自交多边形、EPSG 与 WKT；保留球面距离作为显式选项。
- **Windows 可用性**：修复 FAISS 中文路径读写，检查索引维度和元数据一致性；知识库来源显示相对路径。
- **可复现验证**：41 项自动化测试；40 条离线评测（36 条测绘问题 + 4 条无关问题），独立统计来源命中、MRR、检索覆盖率和回答覆盖率；Windows/Linux CI 验证 JSON/FAISS。

默认 JSON 演示库的 Hit@4 为 **100%**，MRR 为 **0.9583**，离线摘录回答关键词覆盖率为 **79.86%**，4 条无关问题均为空召回。这里是小型演示集结果，不是生产准确率或真实大模型回答质量。完整结果见 [评测报告](docs/eval_report.md) 和 [机器可读结果](docs/eval_results.json)。

## 作者

- 微信：15392993401

## 项目亮点

- **测绘知识库 RAG**：支持 Markdown/TXT 文档入库、切片、索引、检索、上下文拼接和来源追踪。
- **向量后端可切换**：默认使用轻量 JSON 索引，便于本地运行；可切换到 FAISS，后续也可扩展 Milvus/Qdrant。
- **Agent 工具调用**：通过规则识别坐标和意图，调用距离量测、闭合多边形面积计算、坐标转换、WKT 边界框解析；当前是确定性工具路由，不依赖大模型决定调用。
- **三种回答模式**：支持“纯本地知识库匹配”“知识库 + AI”“知识库 + AI + 联网采集”，方便演示不同业务场景下的 RAG 链路。
- **知识库管理界面**：支持网页采集、文件上传、手动录入、默认来源管理、入库文档列表和任务状态追踪。
- **自适应网页爬虫**：支持 URL 自动规范化、HTML 正文抽取、PDF/JSON/纯文本解析、编码识别、标题识别、最终跳转 URL 记录和失败状态反馈。
- **多格式文件上传**：支持 PDF、Word DOCX、Excel XLSX、CSV、JSON、TXT、Markdown 上传后自动解析入库。
- **评测闭环**：内置 40 条评测样本，可生成 Markdown / JSON 报告，分开衡量检索与回答。
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
git clone https://github.com/2809728882/GeoSurveyRAG.git
cd GeoSurveyRAG
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index
uvicorn geosurvey_rag.api:app --reload --host 127.0.0.1 --port 8000
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

### 文件上传入库

适合上传测绘规范、项目报告、质检表、Excel 台账、作业指导书等资料。

支持格式：

```text
.md .txt .csv .tsv .json .pdf .docx .xlsx
```

API 示例：

```bash
curl -X POST http://127.0.0.1:8000/admin/knowledge/upload \
  -F "files=@survey_report.pdf" \
  -F "files=@quality_check.xlsx" \
  -F "category=project-docs" \
  -F "rebuild=true"
```

上传后的原文件会保存到 `data/uploads/`，解析后的知识库 Markdown 会保存到 `data/knowledge/uploads/`。这两个目录默认不会提交到 GitHub。

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
python -m pip install -e ".[faiss]"
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
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4 --report docs\eval_report.md --json docs\eval_results.json
```

当前评测集覆盖无人机航测、WebGIS、GNSS、地籍测量、坐标转换、遥感/LiDAR、RTK、全站仪、水准测量和测量数据清洗。

运行自动化测试：`python -m pytest -q`。测试覆盖实际接口、上传/手动入库后重建检索、异常模型响应、中文路径 FAISS、数值计算及异常输入，不需要 API Key 或联网采集。

## 检索与空间工具示例

```json
{"question":"GNSS 单点定位需要哪些步骤？","mode":"local","source_filter":"gnss_positioning_notes.md","top_k":3}
```

将上述 JSON 提交到 `/chat`；返回片段带 `citation_id`，`retrieval_status` 表明是否存在检索证据。默认 `RETRIEVAL_MODE=hybrid`，可设置为 `vector` 比较单路向量结果。`MIN_SIMILARITY=0.04` 是原始词频余弦阈值；完整 EPSG 标识精确匹配可保留长文档中的相关片段，展示的 RRF 排序分数不是置信概率。

在“知识库 + AI”模式提问以下示例，会触发对应工具：

- `计算 (111.30,30.70) 到 (111.32,30.72) 的距离，单位公里`
- `把 (111.3,30.7) 从 EPSG:4326 转为 EPSG:3857`
- `请计算 POLYGON((0 0,2 0,2 1,0 1,0 0)) 的边界框`

空间接口输入均按 `(经度, 纬度)` / `xy` 顺序处理。距离支持 `m/km`，面积支持 `m2/km2/ha`。非法字段返回 422，非法几何或 CRS 返回 400。面积接口只处理单个无孔、简单地块，输出椭球表面积；工程投影面积、高程基准及地方坐标参数需另行检核。函数名 `polygon_area_lambert` 为兼容旧调用保留，当前 `method` 已改为 `wgs84_geodesic`。

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
