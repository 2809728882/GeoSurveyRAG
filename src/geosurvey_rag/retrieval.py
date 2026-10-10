"""Deterministic BM25 + vector ranking, with no external model downloads."""

from __future__ import annotations

import math
import re
from collections import Counter

from geosurvey_rag.vector_store import DocumentChunk, cosine, embed_text, tokenize


class HybridRetriever:
    def __init__(self, store, mode: str = "hybrid", min_similarity: float = 0.04):
        if mode not in {"hybrid", "vector"}:
            raise ValueError("Retrieval mode must be hybrid or vector.")
        if not 0 <= min_similarity <= 1:
            raise ValueError("Minimum similarity must be between 0 and 1.")
        self.store, self.mode, self.min_similarity = store, mode, min_similarity
        self.counts = [Counter(tokenize(chunk.text)) for chunk in store.chunks]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 1.0
        self.document_frequency = Counter(term for counts in self.counts for term in counts)

    def search(self, query: str, top_k: int = 4, source_filter: str | None = None):
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        query_vector = embed_text(query)
        identifiers = {
            re.sub(r"\s+", "", match).replace("：", ":").lower()
            for match in re.findall(r"(?<![A-Za-z0-9_])EPSG\s*[:：]\s*\d+(?!\d)", query, re.IGNORECASE)
        }
        eligible: dict[str, DocumentChunk] = {}
        for chunk in self.store.chunks:
            if source_filter and source_filter not in chunk.source:
                continue
            # A raw lexical similarity gate is distinct from the RRF ranking score.
            vector = chunk.vector or embed_text(chunk.text)
            similarity = cosine(query_vector, vector)
            normalized = re.sub(r"\s+", "", chunk.text).replace("：", ":").lower()
            exact_identifier = any(
                re.search(re.escape(identifier) + r"(?!\d)", normalized)
                for identifier in identifiers
            )
            if similarity > 0 and (similarity >= self.min_similarity or exact_identifier):
                eligible[chunk.chunk_id] = chunk
        if not eligible:
            return []
        vectors = [
            (chunk, score)
            for chunk, score in self.store.search(query, len(self.store.chunks))
            if chunk.chunk_id in eligible
        ]
        if self.mode == "vector":
            return vectors[:top_k]
        query_terms = set(tokenize(query))
        lexical = []
        n = len(self.counts)
        for chunk, counts, length in zip(self.store.chunks, self.counts, self.lengths):
            if chunk.chunk_id not in eligible:
                continue
            score = 0.0
            for term in query_terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                df = self.document_frequency[term]
                idf = math.log1p((n - df + 0.5) / (df + 0.5))
                denominator = frequency + 1.2 * (0.25 + 0.75 * length / self.average_length)
                score += idf * frequency * 2.2 / denominator
            if score > 0:
                lexical.append((chunk, score))
        lexical.sort(key=lambda item: (-item[1], item[0].chunk_id))
        scores: Counter = Counter()
        for ranking in (vectors, lexical):
            for rank, (chunk, _) in enumerate(ranking, 1):
                scores[chunk.chunk_id] += 30.5 / (60 + rank)
        ranked = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
        return [(eligible[chunk_id], scores[chunk_id]) for chunk_id in ranked[:top_k]]
