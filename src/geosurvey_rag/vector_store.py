from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")


@dataclass
class DocumentChunk:
    chunk_id: str
    source: str
    text: str
    vector: dict[str, float]


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_RE.findall(text):
        token = token.lower()
        tokens.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            for ngram_size in (2, 3, 4):
                if len(token) >= ngram_size:
                    tokens.extend(
                        token[index : index + ngram_size]
                        for index in range(0, len(token) - ngram_size + 1)
                    )
    return tokens


def embed_text(text: str) -> dict[str, float]:
    tokens = tokenize(text)
    if not tokens:
        return {}

    counts: dict[str, float] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0.0) + 1.0

    norm = math.sqrt(sum(value * value for value in counts.values()))
    return {key: value / norm for key, value in counts.items()} if norm else counts


def embed_dense(text: str, dim: int = 384) -> list[float]:
    values = [0.0] * dim
    for token in tokenize(text):
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        values[bucket] += sign
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values] if norm else values


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def stable_id(source: str, text: str, index: int) -> str:
    digest = hashlib.sha1(f"{source}:{index}:{text}".encode("utf-8")).hexdigest()[:12]
    return f"{Path(source).stem}-{digest}"


class JsonVectorStore:
    def __init__(self, index_dir: Path | str) -> None:
        self.index_dir = Path(index_dir)
        self.index_path = self.index_dir / "chunks.jsonl"
        self.chunks: list[DocumentChunk] = []

    def add(self, source: str, text: str, index: int) -> None:
        clean_text = " ".join(text.split())
        if not clean_text:
            return
        self.chunks.append(
            DocumentChunk(
                chunk_id=stable_id(source, clean_text, index),
                source=source,
                text=clean_text,
                vector=embed_text(clean_text),
            )
        )

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("w", encoding="utf-8") as file:
            for chunk in self.chunks:
                file.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    def load(self) -> "JsonVectorStore":
        self.chunks = []
        if not self.index_path.exists():
            return self
        with self.index_path.open("r", encoding="utf-8") as file:
            for line in file:
                item = json.loads(line)
                self.chunks.append(DocumentChunk(**item))
        return self

    def search(self, query: str, top_k: int = 4) -> list[tuple[DocumentChunk, float]]:
        query_vector = embed_text(query)
        scored = [(chunk, cosine(query_vector, chunk.vector)) for chunk in self.chunks]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [item for item in scored[:top_k] if item[1] > 0]


class FaissVectorStore:
    def __init__(self, index_dir: Path | str, dim: int = 384) -> None:
        self.index_dir = Path(index_dir)
        self.dim = dim
        self.faiss_path = self.index_dir / "faiss.index"
        self.meta_path = self.index_dir / "faiss_chunks.jsonl"
        self.chunks: list[DocumentChunk] = []
        self._vectors: list[list[float]] = []
        self.index = None

    def _import_faiss(self):
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "FAISS backend requires optional dependency: pip install -r requirements-llm.txt"
            ) from exc
        return faiss, np

    def add(self, source: str, text: str, index: int) -> None:
        clean_text = " ".join(text.split())
        if not clean_text:
            return
        vector = embed_dense(clean_text, self.dim)
        self._vectors.append(vector)
        self.chunks.append(
            DocumentChunk(
                chunk_id=stable_id(source, clean_text, index),
                source=source,
                text=clean_text,
                vector={},
            )
        )

    def save(self) -> None:
        faiss, np = self._import_faiss()
        self.index_dir.mkdir(parents=True, exist_ok=True)
        index = faiss.IndexFlatIP(self.dim)
        if self._vectors:
            matrix = np.array(self._vectors, dtype="float32")
            index.add(matrix)
        faiss.write_index(index, str(self.faiss_path))
        with self.meta_path.open("w", encoding="utf-8") as file:
            for chunk in self.chunks:
                file.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    def load(self) -> "FaissVectorStore":
        faiss, _np = self._import_faiss()
        self.chunks = []
        if self.faiss_path.exists():
            self.index = faiss.read_index(str(self.faiss_path))
        if self.meta_path.exists():
            with self.meta_path.open("r", encoding="utf-8") as file:
                for line in file:
                    self.chunks.append(DocumentChunk(**json.loads(line)))
        return self

    def search(self, query: str, top_k: int = 4) -> list[tuple[DocumentChunk, float]]:
        if self.index is None or not self.chunks:
            return []
        _faiss, np = self._import_faiss()
        query_vector = np.array([embed_dense(query, self.dim)], dtype="float32")
        scores, ids = self.index.search(query_vector, top_k)
        results: list[tuple[DocumentChunk, float]] = []
        for score, row_id in zip(scores[0], ids[0]):
            if row_id < 0 or row_id >= len(self.chunks):
                continue
            if float(score) > 0:
                results.append((self.chunks[row_id], float(score)))
        return results


def create_vector_store(index_dir: Path | str, backend: str = "json", dim: int = 384):
    normalized = backend.lower()
    if normalized == "faiss":
        return FaissVectorStore(index_dir, dim)
    if normalized in {"json", "local"}:
        return JsonVectorStore(index_dir)
    raise ValueError(f"Unsupported vector backend: {backend}")
