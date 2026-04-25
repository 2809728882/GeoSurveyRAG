# GeoSurveyRAG

GeoSurveyRAG is a geospatial RAG and tool-calling application for surveying, WebGIS, GNSS, cadastral mapping, remote sensing, and field data quality workflows.

It combines a knowledge base, retrieval pipeline, geospatial tools, source management, offline evaluation, and a lightweight WebGIS interface into one deployable FastAPI service.

## Features

- **Geospatial RAG**: ingest Markdown/TXT documents, split them into chunks, index them, retrieve relevant context, and generate traceable answers.
- **Vector backend switch**: use the built-in JSON index for lightweight local demos, or switch to FAISS for a more production-like vector search workflow.
- **Tool calling**: distance measurement, polygon area calculation, coordinate transformation, and WKT bounding-box parsing.
- **Knowledge intake**: add content manually, manage crawler sources, crawl public pages, and rebuild the index automatically.
- **WebGIS interface**: draw points on a map-like canvas, calculate distance/area, ask questions, and inspect index/source status.
- **Evaluation workflow**: run 36 geospatial golden questions and generate a Markdown evaluation report.
- **Deployable service**: FastAPI, Docker, Docker Compose, health checks, environment configuration, and CI workflow.

## Architecture

```text
GeoSurveyRAG/
  src/geosurvey_rag/        # application code
  data/knowledge/           # sample geospatial knowledge base
  data/sources/             # crawler source configuration
  eval/                     # golden questions
  docs/                     # architecture, ingestion, evaluation, vector backend docs
  examples/                 # CLI examples
  tests/                    # unit tests
  web/                      # browser UI served by FastAPI
```

## Quick Start

```powershell
cd D:\github\GeoSurveyRAG
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index
uvicorn geosurvey_rag.api:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Ask a question:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"无人机航测成果入库前需要检查哪些质量项？\"}"
```

Use a geospatial tool:

```bash
curl -X POST http://127.0.0.1:8000/tool/distance \
  -H "Content-Type: application/json" \
  -d "{\"points\":[[111.30,30.70],[111.32,30.72]],\"unit\":\"m\"}"
```

## Knowledge Intake

Manual intake is useful for internal notes, project QA rules, field survey checklists, and operation guides.

```bash
curl -X POST http://127.0.0.1:8000/admin/knowledge/manual \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"RTK 固定解检查规则\",\"category\":\"field-survey\",\"content\":\"RTK 外业采集前应检查固定解比例、PDOP、卫星数和差分延迟。\",\"rebuild\":true}"
```

Crawler intake can synchronize public documentation pages. Default crawler sources are configured in `data/sources/crawler_sources.json`.

```powershell
python -m geosurvey_rag.knowledge_sources list-sources
python -m geosurvey_rag.knowledge_sources add-source --name "EPSG 4490 CGCS2000" --url "https://epsg.io/4490" --tag epsg --tag cgcs2000
python -m geosurvey_rag.knowledge_sources crawl
```

More details: [docs/knowledge_ingestion.md](docs/knowledge_ingestion.md)

## Index Updates

Rebuild manually:

```bash
curl -X POST "http://127.0.0.1:8000/admin/index/rebuild?force=false"
```

Check index status:

```bash
curl http://127.0.0.1:8000/admin/index/status
```

Run the watcher:

```powershell
python -m geosurvey_rag.index_updater --source data\knowledge --index data\index --interval 30
```

Run the watcher with crawler sync first:

```powershell
python -m geosurvey_rag.index_updater --source data\knowledge --index data\index --interval 300 --crawl-first
```

## FAISS Backend

The default backend is a lightweight JSON index. To use FAISS:

```powershell
pip install -r requirements-llm.txt
$env:VECTOR_BACKEND="faiss"
python -m geosurvey_rag.ingestion --source data\knowledge --index data\index --backend faiss
uvicorn geosurvey_rag.api:app --reload --host 0.0.0.0 --port 8000
```

FAISS generates:

```text
data/index/faiss.index
data/index/faiss_chunks.jsonl
```

More details: [docs/vector_backends.md](docs/vector_backends.md)

## Evaluation

Run offline evaluation and generate a report:

```powershell
python -m geosurvey_rag.evaluation --eval eval\golden_questions.json --top-k 4 --report docs\eval_report.md
```

Current evaluation set covers UAV mapping, WebGIS, GNSS, cadastral surveying, coordinate transformation, remote sensing, LiDAR, RTK, total station workflows, leveling, and data cleaning.

More details: [docs/evaluation.md](docs/evaluation.md)

## Docker

```powershell
docker build -t geosurvey-rag:latest .
docker run --rm -p 8000:8000 geosurvey-rag:latest
```

Or:

```powershell
docker compose up --build
```

## Roadmap

- Add Milvus/Qdrant as distributed vector database backends.
- Replace hash embeddings with a real embedding model such as BGE, Qwen Embedding, or OpenAI embeddings.
- Connect PostGIS, GeoServer, ArcGIS REST, or SuperMap iServer for real layer queries.
- Add authentication, audit logs, source-level permissions, and request tracing.
- Add a richer map frontend with real tiles and layer overlays.
