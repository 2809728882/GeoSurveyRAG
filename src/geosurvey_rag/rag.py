from __future__ import annotations

from pathlib import Path

from geosurvey_rag.llm import LocalLLM
from geosurvey_rag.schemas import SourceChunk
from geosurvey_rag.settings import settings
from geosurvey_rag.vector_store import create_vector_store


class RagPipeline:
    def __init__(self, index_dir: Path | str = settings.index_dir) -> None:
        self.store = create_vector_store(index_dir, settings.vector_backend, settings.dense_dim).load()
        self.llm = LocalLLM()

    def answer(self, question: str, top_k: int | None = None, tool_summary: str = "") -> tuple[str, list[SourceChunk]]:
        retrieved = self.store.search(question, top_k or settings.top_k)
        context = "\n\n".join(chunk.text for chunk, _score in retrieved)
        answer = self.llm.generate(question=question, context=context, tool_summary=tool_summary)
        sources = [
            SourceChunk(
                source=chunk.source,
                chunk_id=chunk.chunk_id,
                score=round(score, 4),
                text=chunk.text,
            )
            for chunk, score in retrieved
        ]
        return answer, sources
