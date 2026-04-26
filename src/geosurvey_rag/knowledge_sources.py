from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
from dataclasses import dataclass
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


@dataclass
class CrawledDocument:
    url: str
    final_url: str
    text: str
    title: str
    content_type: str
    charset: str


class TextExtractingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.current_tag = ""

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        self.current_tag = tag
        if tag in {"script", "style", "noscript", "svg", "canvas", "nav", "footer", "header", "aside", "form", "button"}:
            self.skip_depth += 1
        if tag in {"article", "main", "section", "h1", "h2", "h3", "h4", "p", "li", "tr", "pre", "blockquote", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg", "canvas", "nav", "footer", "header", "aside", "form", "button"} and self.skip_depth:
            self.skip_depth -= 1
        if tag in {"title", self.current_tag}:
            self.current_tag = ""
        if tag in {"h1", "h2", "h3", "h4", "p", "li", "tr", "pre", "blockquote"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self.current_tag == "title":
            self.title_parts.append(text)
            return
        if self.current_tag in {"h1", "h2"}:
            self.parts.append(f"\n## {text}\n")
        elif self.current_tag in {"h3", "h4"}:
            self.parts.append(f"\n### {text}\n")
        elif self.current_tag == "li":
            self.parts.append(f"- {text}")
        else:
            self.parts.append(text)

    def text(self) -> str:
        return clean_extracted_text("\n".join(self.parts))

    def title(self) -> str:
        return clean_inline_text(" ".join(self.title_parts))


def clean_inline_text(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def clean_extracted_text(value: str) -> str:
    lines = []
    seen = set()
    for raw_line in value.replace("\r", "\n").split("\n"):
        line = clean_inline_text(raw_line)
        if not line:
            continue
        key = re.sub(r"\s+", " ", line.lower())
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "\n".join(lines)


def slugify(value: str) -> str:
    value = re.sub(r"https?://", "", value.strip().lower())
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    return value.strip("-")[:80] or "knowledge"


def normalize_url(value: str) -> str | None:
    url = value.strip()
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        if "." not in url or any(char.isspace() for char in url):
            return None
        url = f"https://{url}"
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return url


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
        url = normalize_url(source)
        if not url:
            return None
        parsed = urlparse(url)
        return {
            "id": slugify(parsed.netloc + "-" + (parsed.path or "home")),
            "name": parsed.netloc or url,
            "url": url,
            "enabled": True,
            "tags": [],
            "description": "",
        }

    raw_url = source.get("url", "")
    if not isinstance(raw_url, str):
        return None
    url = normalize_url(raw_url)
    if not url:
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
        raise ValueError("Crawler source URL must be a valid http(s) URL or domain name")
    records = [record for record in records if record["id"] != new_record["id"] and record["url"] != new_record["url"]]
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


def detect_charset(raw: bytes, content_type: str) -> str:
    content_match = re.search(r"charset=([\w.-]+)", content_type, re.IGNORECASE)
    if content_match:
        return content_match.group(1)
    head = raw[:4096].decode("ascii", errors="ignore")
    meta_match = re.search(r"<meta[^>]+charset=['\"]?([\w.-]+)", head, re.IGNORECASE)
    if meta_match:
        return meta_match.group(1)
    return ""


def decode_response_text(raw: bytes, content_type: str) -> tuple[str, str]:
    candidates = [detect_charset(raw, content_type), "utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1"]
    seen = set()
    for encoding in candidates:
        if not encoding or encoding.lower() in seen:
            continue
        seen.add(encoding.lower())
        try:
            return raw.decode(encoding), encoding
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def extract_pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF crawling requires pypdf. Run: pip install pypdf") from exc
    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"## Page {index}\n{text.strip()}")
    return clean_extracted_text("\n\n".join(pages))


def extract_document_text(raw: bytes, content_type: str, final_url: str) -> tuple[str, str, str]:
    text, charset = decode_response_text(raw, content_type)
    lower_type = content_type.lower()
    lower_path = urlparse(final_url).path.lower()
    if "pdf" in lower_type or lower_path.endswith(".pdf"):
        return extract_pdf_text(raw), "", charset
    if "json" in lower_type or lower_path.endswith(".json"):
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, ensure_ascii=False, indent=2), "", charset
        except json.JSONDecodeError:
            return clean_extracted_text(text), "", charset
    if "html" in lower_type or "<html" in text[:2000].lower() or "<!doctype html" in text[:2000].lower():
        parser = TextExtractingParser()
        parser.feed(text)
        title = parser.title()
        return parser.text(), title, charset
    return clean_extracted_text(text), "", charset


def fetch_url_document(
    url: str,
    timeout: int = 15,
    max_chars: int = 2_000_000,
    retries: int = 2,
    min_chars: int = 80,
) -> CrawledDocument:
    normalized = normalize_url(url)
    if not normalized:
        raise ValueError("Invalid URL. Use http(s) URL or a domain name.")
    request = Request(
        normalized,
        headers={
            "User-Agent": "GeoSurveyRAG/0.2 adaptive knowledge crawler; contact: 15392993401",
            "Accept": "text/html,application/xhtml+xml,application/pdf,application/json,text/plain;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        },
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read(max_chars)
                content_type = response.headers.get("content-type", "")
                final_url = response.geturl()
            break
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError(f"Failed to fetch {normalized}: {last_error}")

    extracted, title, charset = extract_document_text(raw, content_type, final_url)
    if len(extracted.strip()) < min_chars:
        raise ValueError(f"Fetched content is too short: {len(extracted.strip())} chars")
    return CrawledDocument(
        url=normalized,
        final_url=final_url,
        text=extracted,
        title=title or urlparse(final_url).netloc or normalized,
        content_type=content_type or "unknown",
        charset=charset or "unknown",
    )


def fetch_url_text(
    url: str,
    timeout: int = 15,
    max_chars: int = 2_000_000,
    retries: int = 2,
    min_chars: int = 80,
) -> str:
    return fetch_url_document(url, timeout, max_chars, retries, min_chars).text


def save_crawled_knowledge(
    url: str,
    text: str,
    source_id: str | None = None,
    source_name: str | None = None,
    final_url: str | None = None,
    title: str | None = None,
    content_type: str | None = None,
    charset: str | None = None,
    knowledge_dir: Path = settings.knowledge_dir,
) -> Path:
    parsed = urlparse(final_url or url)
    host = parsed.netloc or "unknown-host"
    target_dir = knowledge_dir / "crawler" / slugify(host)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{slugify(parsed.path or host)}.md"
    display_title = title or f"Crawled: {url}"
    body = [
        "---",
        "source_type: crawler",
        f"source_id: {source_id or slugify(host)}",
        f"source_name: {source_name or host}",
        f"url: {url}",
        f"final_url: {final_url or url}",
        f"title: {display_title}",
        f"host: {host}",
        f"content_type: {content_type or 'unknown'}",
        f"charset: {charset or 'unknown'}",
        f"fetched_at: {now_iso()}",
        f"content_sha1: {content_sha1(text)}",
        "---",
        "",
        f"# {display_title}",
        "",
        f"Source: {final_url or url}",
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
            document = fetch_url_document(url)
            sha1 = content_sha1(document.text)
            path = save_crawled_knowledge(
                document.url,
                document.text,
                record["id"],
                record["name"],
                final_url=document.final_url,
                title=document.title,
                content_type=document.content_type,
                charset=document.charset,
            )
            status = {
                "ok": True,
                "url": document.url,
                "final_url": document.final_url,
                "title": document.title,
                "content_type": document.content_type,
                "charset": document.charset,
                "path": str(path),
                "chars": len(document.text),
                "content_sha1": sha1,
                "fetched_at": now_iso(),
            }
            state[record["id"]] = status
            results.append({"source_id": record["id"], **status})
        except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError, OSError) as exc:
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
