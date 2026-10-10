from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, Field, FiniteFloat, field_validator

LonLat = tuple[
    Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)],
    Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)],
]


class ChatRequest(BaseModel):
    question: str = Field(
        ..., min_length=2, max_length=8000, examples=["无人机航测成果入库前需要检查哪些质量项？"]
    )
    top_k: int | None = Field(default=None, ge=1, le=10)
    use_tools: bool = True
    mode: Literal["local", "knowledge_ai", "knowledge_ai_search"] = "knowledge_ai"
    source_filter: str | None = Field(default=None, min_length=1, max_length=200)
    urls: list[str] | None = None

    @field_validator("question")
    @classmethod
    def strip_question(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("Please enter a question of at least two characters.")
        return value.strip()


class SourceChunk(BaseModel):
    source: str
    chunk_id: str
    score: float
    text: str
    citation_id: str = ""


class ToolCall(BaseModel):
    name: str
    arguments: dict
    result: dict


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    tool_calls: list[ToolCall] = []
    mode: str = "knowledge_ai"
    crawl: dict | None = None
    retrieval_status: Literal["matched", "no_evidence"] = "matched"
    retrieval_method: str = "hybrid"


class DistanceRequest(BaseModel):
    points: list[LonLat] = Field(..., min_length=2, max_length=10000)
    unit: Literal["m", "km"] = "m"
    method: Literal["geodesic", "haversine"] = "geodesic"


class AreaRequest(BaseModel):
    polygon: list[LonLat] = Field(..., min_length=3, max_length=10000)
    unit: Literal["m2", "km2", "ha"] = "m2"


class TransformRequest(BaseModel):
    x: FiniteFloat
    y: FiniteFloat
    from_epsg: int = Field(default=4326, gt=0)
    to_epsg: int = Field(default=3857, gt=0)


class WktRequest(BaseModel):
    wkt: str = Field(min_length=5, max_length=100000)


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
