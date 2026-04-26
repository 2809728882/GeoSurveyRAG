from __future__ import annotations

import re
from pathlib import Path

from geosurvey_rag.llm import create_llm
from geosurvey_rag.schemas import SourceChunk
from geosurvey_rag.settings import settings
from geosurvey_rag.vector_store import create_vector_store


class RagPipeline:
    def __init__(self, index_dir: Path | str = settings.index_dir) -> None:
        self.store = create_vector_store(index_dir, settings.vector_backend, settings.dense_dim).load()
        self.llm = create_llm()

    def retrieve(self, question: str, top_k: int | None = None) -> list[tuple[object, float]]:
        return self.store.search(question, top_k or settings.top_k)

    def format_local_answer(self, question: str, retrieved: list[tuple[object, float]]) -> str:
        if not retrieved:
            return (
                "当前知识库没有匹配到足够相关的内容。\n"
                "建议先上传项目报告、测绘规范、质检清单，或使用联网采集补充资料后再提问。\n"
                f"问题：{question}"
            )
        lines = ["本地知识库匹配结果", ""]
        for index, (chunk, score) in enumerate(retrieved, start=1):
            text = clean_display_text(chunk.text)
            if len(text) > 320:
                text = text[:320].rstrip() + "..."
            lines.extend(
                [
                    f"{index}. 匹配度 {score:.4f}",
                    f"来源：{chunk.source}",
                    f"内容：{text}",
                    "",
                ]
            )
        lines.append("说明：当前模式只做本地知识库检索，不调用大模型生成。")
        return "\n".join(lines).strip()

    def answer_local(self, question: str, top_k: int | None = None) -> tuple[str, list[SourceChunk]]:
        retrieved = self.retrieve(question, top_k)
        sources = [
            SourceChunk(
                source=chunk.source,
                chunk_id=chunk.chunk_id,
                score=round(score, 4),
                text=clean_display_text(chunk.text),
            )
            for chunk, score in retrieved
        ]
        return self.format_local_answer(question, retrieved), sources

    def answer(self, question: str, top_k: int | None = None, tool_summary: str = "") -> tuple[str, list[SourceChunk]]:
        retrieved = self.retrieve(question, top_k)
        context = "\n\n".join(clean_display_text(chunk.text) for chunk, _score in retrieved)
        answer = self.llm.generate(question=question, context=context, tool_summary=tool_summary)
        sources = [
            SourceChunk(
                source=chunk.source,
                chunk_id=chunk.chunk_id,
                score=round(score, 4),
                text=clean_display_text(chunk.text),
            )
            for chunk, score in retrieved
        ]
        return answer, sources


def clean_display_text(text: str) -> str:
    text = re.sub(r"^---\s*.*?^---\s*", "", text, flags=re.DOTALL | re.MULTILINE)
    text = re.sub(r"^---\s+.*?\s+---\s*", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<=\s)#{1,6}\s*", "", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+[-*+]\s+", "；", text)
    text = re.sub(r"：；", "：", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return " ".join(text.split())
