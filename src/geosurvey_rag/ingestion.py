from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from geosurvey_rag.settings import settings
from geosurvey_rag.vector_store import create_vector_store


SUPPORTED_EXTENSIONS = {".md", ".txt"}


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def iter_documents(source_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def file_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(source_dir: Path, documents: list[Path], chunk_count: int, backend: str) -> dict:
    return {
        "source_dir": str(source_dir),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "vector_backend": backend,
        "document_count": len(documents),
        "chunk_count": chunk_count,
        "documents": [
            {
                "path": str(path),
                "sha1": file_sha1(path),
                "size": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            }
            for path in documents
        ],
    }


def load_manifest(index_dir: Path) -> dict | None:
    manifest_path = index_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def knowledge_changed(source_dir: Path, index_dir: Path) -> bool:
    documents = iter_documents(source_dir)
    current = build_manifest(source_dir, documents, chunk_count=0, backend=settings.vector_backend)
    previous = load_manifest(index_dir)
    if previous is None:
        return True
    previous_docs = {item["path"]: item["sha1"] for item in previous.get("documents", [])}
    current_docs = {item["path"]: item["sha1"] for item in current["documents"]}
    return previous_docs != current_docs or previous.get("vector_backend") != settings.vector_backend


def build_index(source_dir: Path, index_dir: Path, backend: str | None = None) -> int:
    selected_backend = backend or settings.vector_backend
    store = create_vector_store(index_dir, selected_backend, settings.dense_dim)
    documents = iter_documents(source_dir)
    count = 0
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for index, chunk in enumerate(split_text(text, settings.chunk_size, settings.chunk_overlap)):
            store.add(str(path), chunk, index)
            count += 1
    store.save()
    manifest = build_manifest(source_dir, documents, count, selected_backend)
    (index_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build GeoSurveyRAG local vector index.")
    parser.add_argument("--source", type=Path, default=settings.knowledge_dir)
    parser.add_argument("--index", type=Path, default=settings.index_dir)
    parser.add_argument("--backend", default=settings.vector_backend, choices=["json", "faiss"])
    args = parser.parse_args()
    count = build_index(args.source, args.index, args.backend)
    print(f"Indexed {count} chunks from {args.source} into {args.index} with {args.backend}")


if __name__ == "__main__":
    main()
