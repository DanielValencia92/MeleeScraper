import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from selectolax.parser import HTMLParser

from .models import EventRecord
from .normalize import normalize_format


def source_event_id(url: str) -> str:
    """Stable, source-local fallback ID derived from a public URL."""
    parsed = urlparse(url)
    token = re.sub(r"[^A-Za-z0-9_-]+", "-", parsed.path.strip("/")).strip("-")
    return token or parsed.netloc


def _meta(tree: HTMLParser, property_name: str) -> str | None:
    node = tree.css_first(f'meta[property="{property_name}"], meta[name="{property_name}"]')
    return node.attributes.get("content", "").strip() or None if node else None


def parse_public_page(url: str, html: str, snapshot_path: Path, source: str) -> EventRecord:
    tree = HTMLParser(html)
    title = _meta(tree, "og:title") or (tree.css_first("title").text(strip=True) if tree.css_first("title") else None)
    description = _meta(tree, "og:description") or _meta(tree, "description")
    visible_text = tree.body.text(separator=" ", strip=True) if tree.body else ""
    format_raw = _meta(tree, "event:format")
    return EventRecord(
        source=source,
        source_event_id=source_event_id(url),
        url=url,
        name=title,
        game="Star Wars: Unlimited" if "star wars" in visible_text.casefold() or "swu" in visible_text.casefold() else None,
        format_raw=format_raw,
        format_norm=normalize_format(title, description, format_raw, visible_text),
        tags=[],
        crawled_at=datetime.now(timezone.utc),
        raw_snapshot_path=str(snapshot_path),
    )


def record_json(record: EventRecord) -> str:
    return json.dumps(record.model_dump(mode="json"), sort_keys=True)

