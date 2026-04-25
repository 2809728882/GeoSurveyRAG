from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from geosurvey_rag.agent import GeoAgent, format_tool_summary
from geosurvey_rag.index_updater import reindex_if_needed
from geosurvey_rag.ingestion import load_manifest
from geosurvey_rag.knowledge_sources import crawl_sources, save_manual_knowledge
from geosurvey_rag.knowledge_sources import (
    add_crawler_source,
    list_crawler_sources,
    remove_crawler_source,
    set_crawler_source_enabled,
)
from geosurvey_rag.rag import RagPipeline
from geosurvey_rag.schemas import (
    AreaRequest,
    CrawlAndChatRequest,
    CrawlKnowledgeRequest,
    CrawlerSourceRequest,
    CrawlerSourceToggleRequest,
    ChatRequest,
    ChatResponse,
    DistanceRequest,
    ManualKnowledgeRequest,
    TransformRequest,
    WktRequest,
)
from geosurvey_rag.settings import settings
from geosurvey_rag.tools.geodesy import (
    haversine_distance,
    polygon_area_lambert,
    transform_coordinate,
    wkt_bbox,
)

app = FastAPI(title=settings.app_name, version="0.1.0")
rag = RagPipeline(settings.index_dir)
agent = GeoAgent()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/")
def web_app() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/admin/index/status")
def index_status() -> dict:
    manifest = load_manifest(settings.index_dir)
    return {
        "ready": manifest is not None,
        "manifest": manifest or {},
    }


@app.post("/admin/index/rebuild")
def rebuild_index(force: bool = False, crawl_first: bool = False) -> dict:
    global rag
    result = reindex_if_needed(
        settings.knowledge_dir,
        settings.index_dir,
        force=force,
        crawl_first=crawl_first,
    )
    if result["updated"]:
        rag = RagPipeline(settings.index_dir)
    return result


@app.post("/admin/knowledge/manual")
def manual_knowledge(request: ManualKnowledgeRequest) -> dict:
    global rag
    path = save_manual_knowledge(request.title, request.content, request.category)
    result = None
    if request.rebuild:
        result = reindex_if_needed(settings.knowledge_dir, settings.index_dir, force=True)
        rag = RagPipeline(settings.index_dir)
    return {"ok": True, "path": str(path), "index": result}


@app.post("/admin/knowledge/crawl")
def crawl_knowledge(request: CrawlKnowledgeRequest) -> dict:
    global rag
    crawl_result = crawl_sources(request.urls)
    index_result = None
    if request.rebuild:
        index_result = reindex_if_needed(settings.knowledge_dir, settings.index_dir, force=True)
        rag = RagPipeline(settings.index_dir)
    return {"ok": True, "crawl": crawl_result, "index": index_result}


@app.post("/admin/knowledge/crawl-and-chat")
def crawl_and_chat(request: CrawlAndChatRequest) -> dict:
    global rag
    crawl_result = crawl_sources(request.urls)
    index_result = reindex_if_needed(settings.knowledge_dir, settings.index_dir, force=True)
    rag = RagPipeline(settings.index_dir)
    answer, sources = rag.answer(request.question, top_k=request.top_k)
    return {
        "ok": True,
        "crawl": crawl_result,
        "index": index_result,
        "answer": answer,
        "sources": sources,
    }


@app.get("/admin/knowledge/crawler-sources")
def crawler_sources() -> dict:
    return list_crawler_sources()


@app.post("/admin/knowledge/crawler-sources")
def add_source(request: CrawlerSourceRequest) -> dict:
    source = add_crawler_source(
        request.url,
        request.name,
        enabled=request.enabled,
        tags=request.tags,
        description=request.description,
    )
    return {"ok": True, "source": source}


@app.patch("/admin/knowledge/crawler-sources/{source_id}")
def toggle_source(source_id: str, request: CrawlerSourceToggleRequest) -> dict:
    source = set_crawler_source_enabled(source_id, request.enabled)
    return {"ok": source is not None, "source": source}


@app.delete("/admin/knowledge/crawler-sources/{source_id}")
def delete_source(source_id: str) -> dict:
    return {"ok": remove_crawler_source(source_id)}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    tool_calls = agent.maybe_run_tools(request.question) if request.use_tools else []
    answer, sources = rag.answer(
        request.question,
        top_k=request.top_k,
        tool_summary=format_tool_summary(tool_calls),
    )
    return ChatResponse(answer=answer, sources=sources, tool_calls=tool_calls)


@app.post("/tool/distance")
def distance(request: DistanceRequest) -> dict:
    return haversine_distance(request.points, request.unit)


@app.post("/tool/area")
def area(request: AreaRequest) -> dict:
    return polygon_area_lambert(request.polygon, request.unit)


@app.post("/tool/transform")
def transform(request: TransformRequest) -> dict:
    return transform_coordinate(request.x, request.y, request.from_epsg, request.to_epsg)


@app.post("/tool/wkt-bbox")
def bbox(request: WktRequest) -> dict:
    return wkt_bbox(request.wkt)


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
