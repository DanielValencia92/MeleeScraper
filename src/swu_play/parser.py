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


def _text(tree: HTMLParser, selector: str) -> str | None:
    node = tree.css_first(selector)
    return node.text(separator=" ", strip=True) or None if node else None


def melee_venue_id(html: str) -> int | None:
    """Return the public venue ID embedded in a Melee tournament page."""
    tree = HTMLParser(html)
    node = tree.css_first('[data-type="venue"][data-id]')
    if not node:
        return None
    try:
        return int(node.attributes["data-id"])
    except (KeyError, ValueError):
        return None


def _parse_melee_page(tree: HTMLParser) -> dict[str, object]:
    registration = _text(tree, "#tournament-headline-registration")
    match = re.search(r"\bFormat:\s*([^|]+)", registration or "", flags=re.IGNORECASE)
    format_raw = match.group(1).strip() if match else None
    players = re.search(r"\b(\d+)\s+of\s+\d+\s+Enrolled Players\b", registration or "", flags=re.IGNORECASE)
    date_node = tree.css_first("#tournament-headline-start-date-field [data-value]")
    organization = _text(tree, "#tournament-headline-organization a")
    venue = _text(tree, '[data-type="venue"]')
    game = (_text(tree, "#tournament-headline-game") or "").removeprefix("Game:").strip() or None
    if game and "star wars" in game.casefold() and "unlimited" in game.casefold():
        game = "Star Wars: Unlimited"
    return {
        "start_date": date_node.attributes.get("data-value", "")[:10] or None if date_node else None,
        "game": game,
        "format_raw": format_raw,
        "organization": organization,
        "venue": venue,
        "player_count": int(players.group(1)) if players else None,
    }


def parse_public_page(url: str, html: str, snapshot_path: Path, source: str) -> EventRecord:
    tree = HTMLParser(html)
    title = _meta(tree, "og:title") or (tree.css_first("title").text(strip=True) if tree.css_first("title") else None)
    description = _meta(tree, "og:description") or _meta(tree, "description")
    is_melee_tournament = urlparse(url).netloc.casefold() == "melee.gg" and urlparse(url).path.casefold().startswith("/tournament/view/")
    melee = _parse_melee_page(tree) if is_melee_tournament else {}
    format_raw = melee.get("format_raw") or _meta(tree, "event:format")
    return EventRecord(
        source=source,
        source_event_id=source_event_id(url),
        url=url,
        name=title,
        start_date=melee.get("start_date"),
        game=melee.get("game") or ("Star Wars: Unlimited" if "star wars" in (tree.body.text(separator=" ", strip=True) if tree.body else "").casefold() or "swu" in (tree.body.text(separator=" ", strip=True) if tree.body else "").casefold() else None),
        format_raw=format_raw,
        format_norm=normalize_format(format_raw, title, description),
        organization=melee.get("organization"),
        venue=melee.get("venue"),
        player_count=melee.get("player_count"),
        tags=[],
        crawled_at=datetime.now(timezone.utc),
        raw_snapshot_path=str(snapshot_path),
    )


def record_json(record: EventRecord) -> str:
    return json.dumps(record.model_dump(mode="json"), sort_keys=True)
