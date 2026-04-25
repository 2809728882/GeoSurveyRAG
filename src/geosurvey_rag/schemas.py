from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, examples=["无人机航测成果入库前需要检查哪些质量项？"])
    top_k: int | None = Field(default=None, ge=1, le=10)
    use_tools: bool = True


class SourceChunk(BaseModel):
    source: str
    chunk_id: str
    score: float
    text: str


class ToolCall(BaseModel):
    name: str
    arguments: dict
    result: dict


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    tool_calls: list[ToolCall] = []


class DistanceRequest(BaseModel):
    points: list[tuple[float, float]] = Field(..., min_length=2)
    unit: str = "m"


class AreaRequest(BaseModel):
    polygon: list[tuple[float, float]] = Field(..., min_length=3)
    unit: str = "m2"


class TransformRequest(BaseModel):
    x: float
    y: float
    from_epsg: int = 4326
    to_epsg: int = 3857


class WktRequest(BaseModel):
    wkt: str


class ManualKnowledgeRequest(BaseModel):
    title: str = Field(..., min_length=2)
    content: str = Field(..., min_length=10)
    category: str = "manual"
    rebuild: bool = True


class CrawlKnowledgeRequest(BaseModel):
    urls: list[str] | None = None
    rebuild: bool = True


class CrawlAndChatRequest(BaseModel):
    question: str = Field(..., min_length=2)
    urls: list[str] = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)


class CrawlerSourceRequest(BaseModel):
    url: str = Field(..., min_length=8)
    name: str | None = None
    enabled: bool = True
    tags: list[str] = []
    description: str = ""


class CrawlerSourceToggleRequest(BaseModel):
    enabled: bool
