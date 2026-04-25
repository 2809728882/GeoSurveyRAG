from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from geosurvey_rag.settings import settings


SOURCE_CONFIG = Path("data/sources/crawler_sources.json")
CRAWLER_STATE = Path("data/sources/crawler_state.json")
DEFAULT_CRAWLER_SOURCES = [
    {
        "id": "epsg-4326",
        "name": "EPSG 4326 WGS84",
        "url": "https://epsg.io/4326",
        "enabled": True,
        "tags": ["coordinate-system", "epsg", "webgis"],
        "description": "WGS84 geographic coordinate system reference.",
    },
    {
        "id": "epsg-3857",
        "name": "EPSG 3857 Web Mercator",
        "url": "https://epsg.io/3857",
        "enabled": True,
        "tags": ["coordinate-system", "epsg", "webgis"],
        "description": "Web Mercator coordinate system reference.",
    },
    {
        "id": "ogc-geojson",
        "name": "OGC GeoJSON Standard",
        "url": "https://docs.ogc.org/is/17-069r3/17-069r3.html",
        "enabled": False,
        "tags": ["ogc", "webgis", "geojson"],
        "description": "Public OGC GeoJSON standard page. Disabled by default to keep demos light.",
    },
    {
        "id": "ogc-api-features",
        "name": "OGC API Features",
        "url": "https://docs.ogc.org/is/17-069r4/17-069r4.html",
        "enabled": False,
        "tags": ["ogc", "api", "webgis"],
        "description": "Public OGC API Features reference. Enable when network is available.",
    },
]


class TextExtractingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip = False

    def handle_data(self, data: str) -> None:
        if not self.skip:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


def slugify(value: str) -> str:
    value = re.sub(r"https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-")[:80] or "knowledge"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def save_manual_knowledge(
    title: str,
    content: str,
    category: str = "manual",
    knowledge_dir: Path = settings.knowledge_dir,
) -> Path:
    target_dir = knowledge_dir / "manual" / slugify(category)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{slugify(title)}.md"
    body = [
        "---",
        "source_type: manual",
        f"title: {title}",
        f"category: {category}",
        f"created_at: {now_iso()}",
        "---",
        "",
        f"# {title}",
        "",
        content.strip(),
        "",
    ]
    target.write_text("\n".join(body), encoding="utf-8")
    return target


def ensure_source_config(config_path: Path = SOURCE_CONFIG) -> None:
    if config_path.exists():
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"sources": DEFAULT_CRAWLER_SOURCES}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_source(source: dict | str) -> dict | None:
    if isinstance(source, str):
        if not source.startswith(("http://", "https://")):
            return None
        parsed = urlparse(source)
        return {
            "id": slugify(parsed.netloc + "-" + (parsed.path or "home")),
            "name": parsed.netloc or source,
            "url": source,
            "enabled": True,
            "tags": [],
            "description": "",
        }

    url = source.get("url", "")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None
    parsed = urlparse(url)
    source_id = source.get("id") or slugify(parsed.netloc + "-" + (parsed.path or "home"))
    return {
        "id": slugify(str(source_id)),
        "name": str(source.get("name") or parsed.netloc or url),
        "url": url,
        "enabled": bool(source.get("enabled", True)),
        "tags": [str(tag) for tag in source.get("tags", [])],
        "description": str(source.get("description", "")),
    }


def load_crawler_source_records(config_path: Path = SOURCE_CONFIG) -> list[dict]:
    ensure_source_config(config_path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    raw_sources = data.get("sources")
    if raw_sources is None:
        raw_sources = data.get("urls", data if isinstance(data, list) else [])
    records = [item for item in (normalize_source(source) for source in raw_sources) if item]
    seen = set()
    unique = []
    for record in records:
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        unique.append(record)
    return unique


def save_crawler_source_records(records: list[dict], config_path: Path = SOURCE_CONFIG) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"sources": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_crawler_sources(config_path: Path = SOURCE_CONFIG) -> dict:
    records = load_crawler_source_records(config_path)
    state = load_crawler_state()
    return {
        "count": len(records),
        "enabled_count": sum(1 for record in records if record["enabled"]),
        "sources": [
            {
                **record,
                "last_status": state.get(record["id"], {}),
            }
            for record in records
        ],
    }


def add_crawler_source(
    url: str,
    name: str | None = None,
    enabled: bool = True,
    tags: list[str] | None = None,
    description: str = "",
    config_path: Path = SOURCE_CONFIG,
) -> dict:
    records = load_crawler_source_records(config_path)
    new_record = normalize_source(
        {
            "url": url,
            "name": name,
            "enabled": enabled,
            "tags": tags or [],
            "description": description,
        }
    )
    if new_record is None:
        raise ValueError("Crawler source URL must start with http:// or https://")
    records = [record for record in records if record["id"] != new_record["id"] and record["url"] != url]
    records.append(new_record)
    save_crawler_source_records(records, config_path)
    return new_record


def remove_crawler_source(source_id: str, config_path: Path = SOURCE_CONFIG) -> bool:
    records = load_crawler_source_records(config_path)
    filtered = [record for record in records if record["id"] != source_id]
    save_crawler_source_records(filtered, config_path)
    return len(filtered) != len(records)


def set_crawler_source_enabled(source_id: str, enabled: bool, config_path: Path = SOURCE_CONFIG) -> dict | None:
    records = load_crawler_source_records(config_path)
    updated = None
    for record in records:
        if record["id"] == source_id:
            record["enabled"] = enabled
            updated = record
            break
    save_crawler_source_records(records, config_path)
    return updated


def load_crawler_state(state_path: Path = CRAWLER_STATE) -> dict:
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text(encoding="utf-8"))


def save_crawler_state(state: dict, state_path: Path = CRAWLER_STATE) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_crawler_sources(config_path: Path = SOURCE_CONFIG, enabled_only: bool = True) -> list[str]:
    records = load_crawler_source_records(config_path)
    return [
        record["url"]
        for record in records
        if record["enabled"] or not enabled_only
    ]


def fetch_url_text(
    url: str,
    timeout: int = 15,
    max_chars: int = 120_000,
    retries: int = 2,
    min_chars: int = 80,
) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "GeoSurveyRAG/0.1 knowledge crawler; educational project",
            "Accept": "text/html, text/plain;q=0.9,*/*;q=0.8",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(max_chars)
                content_type = response.headers.get("content-type", "")
            break
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError(f"Failed to fetch {url}: {last_error}")

    text = raw.decode("utf-8", errors="ignore")
    if "html" not in content_type and "<html" not in text.lower():
        extracted = text
    else:
        parser = TextExtractingParser()
        parser.feed(text)
        extracted = parser.text()
    if len(extracted.strip()) < min_chars:
        raise ValueError(f"Fetched content is too short: {len(extracted.strip())} chars")
    return extracted


def save_crawled_knowledge(
    url: str,
    text: str,
    source_id: str | None = None,
    source_name: str | None = None,
    knowledge_dir: Path = settings.knowledge_dir,
) -> Path:
    parsed = urlparse(url)
    host = parsed.netloc or "unknown-host"
    target_dir = knowledge_dir / "crawler" / slugify(host)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{slugify(parsed.path or host)}.md"
    body = [
        "---",
        "source_type: crawler",
        f"source_id: {source_id or slugify(host)}",
        f"source_name: {source_name or host}",
        f"url: {url}",
        f"host: {host}",
        f"fetched_at: {now_iso()}",
        f"content_sha1: {content_sha1(text)}",
        "---",
        "",
        f"# Crawled: {url}",
        "",
        text.strip(),
        "",
    ]
    target.write_text("\n".join(body), encoding="utf-8")
    return target


def crawl_sources(urls: list[str] | None = None, delay_seconds: float = 1.0) -> dict:
    if urls:
        records = [normalize_source(url) for url in urls]
        selected_records = [record for record in records if record]
    else:
        selected_records = [
            record for record in load_crawler_source_records() if record["enabled"]
        ]
    state = load_crawler_state()
    results = []
    for record in selected_records:
        url = record["url"]
        try:
            text = fetch_url_text(url)
            sha1 = content_sha1(text)
            path = save_crawled_knowledge(url, text, record["id"], record["name"])
            status = {
                "ok": True,
                "url": url,
                "path": str(path),
                "chars": len(text),
                "content_sha1": sha1,
                "fetched_at": now_iso(),
            }
            state[record["id"]] = status
            results.append({"source_id": record["id"], **status})
        except (URLError, TimeoutError, ValueError, OSError) as exc:
            status = {
                "ok": False,
                "url": url,
                "error": str(exc),
                "fetched_at": now_iso(),
            }
            state[record["id"]] = status
            results.append({"source_id": record["id"], **status})
        time.sleep(delay_seconds)
    save_crawler_state(state)
    return {
        "source_type": "crawler",
        "count": len(results),
        "success": sum(1 for item in results if item["ok"]),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage manual and crawler knowledge sources.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    manual = subparsers.add_parser("manual")
    manual.add_argument("--title", required=True)
    manual.add_argument("--content", required=True)
    manual.add_argument("--category", default="manual")

    crawl = subparsers.add_parser("crawl")
    crawl.add_argument("--url", action="append", default=None)

    subparsers.add_parser("list-sources")

    add_source = subparsers.add_parser("add-source")
    add_source.add_argument("--url", required=True)
    add_source.add_argument("--name", default=None)
    add_source.add_argument("--tag", action="append", default=[])
    add_source.add_argument("--disabled", action="store_true")
    add_source.add_argument("--description", default="")

    remove_source = subparsers.add_parser("remove-source")
    remove_source.add_argument("--id", required=True)

    enable_source = subparsers.add_parser("enable-source")
    enable_source.add_argument("--id", required=True)
    disable_source = subparsers.add_parser("disable-source")
    disable_source.add_argument("--id", required=True)

    args = parser.parse_args()
    if args.command == "manual":
        path = save_manual_knowledge(args.title, args.content, args.category)
        print(json.dumps({"ok": True, "path": str(path)}, ensure_ascii=False, indent=2))
    elif args.command == "crawl":
        print(json.dumps(crawl_sources(args.url), ensure_ascii=False, indent=2))
    elif args.command == "list-sources":
        print(json.dumps(list_crawler_sources(), ensure_ascii=False, indent=2))
    elif args.command == "add-source":
        record = add_crawler_source(
            args.url,
            args.name,
            enabled=not args.disabled,
            tags=args.tag,
            description=args.description,
        )
        print(json.dumps({"ok": True, "source": record}, ensure_ascii=False, indent=2))
    elif args.command == "remove-source":
        print(json.dumps({"ok": remove_crawler_source(args.id)}, ensure_ascii=False, indent=2))
    elif args.command == "enable-source":
        print(json.dumps({"source": set_crawler_source_enabled(args.id, True)}, ensure_ascii=False, indent=2))
    elif args.command == "disable-source":
        print(json.dumps({"source": set_crawler_source_enabled(args.id, False)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
