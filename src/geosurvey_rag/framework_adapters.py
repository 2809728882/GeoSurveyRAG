from __future__ import annotations

from typing import Any

from geosurvey_rag.vector_store import JsonVectorStore


def export_langchain_documents(index_dir: str = "data/index") -> list[Any]:
    """Export local chunks as LangChain Document objects when LangChain is installed."""
    try:
        from langchain_core.documents import Document
    except ImportError as exc:
        raise RuntimeError("Install langchain to use this adapter: pip install langchain") from exc

    store = JsonVectorStore(index_dir).load()
    return [
        Document(page_content=chunk.text, metadata={"source": chunk.source, "chunk_id": chunk.chunk_id})
        for chunk in store.chunks
    ]


def export_llama_index_documents(index_dir: str = "data/index") -> list[Any]:
    """Export local chunks as LlamaIndex Document objects when llama-index is installed."""
    try:
        from llama_index.core import Document
    except ImportError as exc:
        raise RuntimeError("Install llama-index to use this adapter: pip install llama-index") from exc

    store = JsonVectorStore(index_dir).load()
    return [
        Document(text=chunk.text, metadata={"source": chunk.source, "chunk_id": chunk.chunk_id})
        for chunk in store.chunks
    ]
