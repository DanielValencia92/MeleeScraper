import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .db import connect
from .models import EventRecord
from .parser import melee_venue_id, parse_public_page, record_json


def import_url_values(db_path: Path, urls: list[str], source: str) -> tuple[int, int]:
    connection = connect(db_path)
    added = duplicate = 0
    for url in urls:
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        cursor = connection.execute(
            "INSERT OR IGNORE INTO discovered_urls (url, source) VALUES (?, ?)", (url, source)
        )
        if cursor.rowcount:
            added += 1
        else:
            duplicate += 1
            connection.execute("UPDATE discovered_urls SET last_seen = CURRENT_TIMESTAMP WHERE url = ?", (url,))
    connection.commit()
    return added, duplicate


def import_urls(db_path: Path, input_path: Path, source: str) -> tuple[int, int]:
    return import_url_values(db_path, input_path.read_text(encoding="utf-8").splitlines(), source)


def crawl_pending(
    db_path: Path,
    raw_dir: Path,
    delay_seconds: float,
    refresh: bool = False,
    limit: int | None = None,
) -> dict[str, int]:
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least one.")
    connection = connect(db_path)
    query = "SELECT url, source FROM discovered_urls" if refresh else "SELECT url, source FROM discovered_urls WHERE status != 'ok'"
    query += " ORDER BY first_seen, url"
    parameters: tuple[int, ...] = ()
    if limit is not None:
        query += " LIMIT ?"
        parameters = (limit,)
    rows = connection.execute(query, parameters).fetchall()
    counts = {"attempted": 0, "ok": 0, "failed": 0}
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Melee's public HTML endpoints reject non-browser client identifiers.
    # These are the same request headers used by the Melee discovery adapter;
    # no authentication, private API, or participant data is involved.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        for row in rows:
            counts["attempted"] += 1
            url, source = row["url"], row["source"]
            try:
                response = client.get(url)
                response.raise_for_status()
                digest = hashlib.sha256(response.content).hexdigest()
                host = urlparse(url).netloc.replace(".", "_")
                snapshot = raw_dir / host / f"{digest}.html"
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                if not snapshot.exists():
                    snapshot.write_bytes(response.content)
                record = parse_public_page(url, response.text, snapshot, source)
                connection.execute(
                    "INSERT INTO events (url, source, source_event_id, payload_json) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(url) DO UPDATE SET source=excluded.source, source_event_id=excluded.source_event_id, payload_json=excluded.payload_json, updated_at=CURRENT_TIMESTAMP",
                    (url, source, record.source_event_id, record_json(record)),
                )
                connection.execute(
                    "UPDATE discovered_urls SET status='ok', last_http_status=?, content_hash=?, last_crawled_at=?, error=NULL WHERE url=?",
                    (response.status_code, digest, datetime.now(timezone.utc).isoformat(), url),
                )
                counts["ok"] += 1
            except (httpx.HTTPError, ValueError) as error:
                connection.execute(
                    "UPDATE discovered_urls SET status='failed', error=?, last_crawled_at=? WHERE url=?",
                    (str(error)[:1000], datetime.now(timezone.utc).isoformat(), url),
                )
                counts["failed"] += 1
            connection.commit()
            time.sleep(delay_seconds)
    return counts


def reparse_archived(db_path: Path) -> dict[str, int]:
    """Rebuild event records from archived raw pages without another network request."""
    connection = connect(db_path)
    counts = {"attempted": 0, "updated": 0, "missing_snapshot": 0}
    rows = connection.execute("SELECT url, source, payload_json FROM events ORDER BY url").fetchall()
    for row in rows:
        counts["attempted"] += 1
        payload = json.loads(row["payload_json"])
        snapshot = Path(payload["raw_snapshot_path"])
        if not snapshot.exists():
            counts["missing_snapshot"] += 1
            continue
        record = parse_public_page(row["url"], snapshot.read_text(encoding="utf-8"), snapshot, row["source"])
        connection.execute(
            "UPDATE events SET source_event_id=?, payload_json=?, updated_at=CURRENT_TIMESTAMP WHERE url=?",
            (record.source_event_id, record_json(record), row["url"]),
        )
        counts["updated"] += 1
    connection.commit()
    return counts


def enrich_melee_venues(db_path: Path, delay_seconds: float, limit: int | None = None) -> dict[str, int]:
    """Attach public city/region/country data from Melee venue cards, with caching."""
    if delay_seconds < 5:
        raise ValueError("Melee's robots.txt specifies a five-second crawl delay.")
    if limit is not None and limit < 1:
        raise ValueError("limit must be at least one.")
    connection = connect(db_path)
    event_venues: dict[str, int] = {}
    for row in connection.execute("SELECT url, payload_json FROM events WHERE url LIKE 'https://melee.gg/Tournament/View/%'"):
        payload = json.loads(row["payload_json"])
        snapshot = Path(payload["raw_snapshot_path"])
        if snapshot.exists():
            venue_id = melee_venue_id(snapshot.read_text(encoding="utf-8"))
            if venue_id is not None:
                event_venues[row["url"]] = venue_id
    cached = {row["venue_id"] for row in connection.execute("SELECT venue_id FROM melee_venues")}
    pending = sorted(set(event_venues.values()) - cached)
    if limit is not None:
        pending = pending[:limit]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    counts = {"events_with_venue": len(event_venues), "venues_requested": 0, "venues_cached": len(cached), "venue_failures": 0, "events_enriched": 0}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
        for venue_id in pending:
            counts["venues_requested"] += 1
            try:
                data = client.get(f"https://melee.gg/Venue/GetDetails?id={venue_id}").raise_for_status().json()
                connection.execute(
                    "INSERT OR REPLACE INTO melee_venues (venue_id, name, city, region, country, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (venue_id, data.get("Name"), data.get("AddressCity"), data.get("AddressState"), data.get("AddressCountry"), datetime.now(timezone.utc).isoformat()),
                )
                connection.commit()
            except (httpx.HTTPError, ValueError):
                counts["venue_failures"] += 1
            time.sleep(delay_seconds)
    venues = {row["venue_id"]: dict(row) for row in connection.execute("SELECT venue_id, city, region, country FROM melee_venues")}
    for row in connection.execute("SELECT url, payload_json FROM events").fetchall():
        venue = venues.get(event_venues.get(row["url"]))
        if not venue:
            continue
        record = EventRecord.model_validate(json.loads(row["payload_json"]))
        record.city, record.region, record.country = venue["city"], venue["region"], venue["country"]
        connection.execute("UPDATE events SET payload_json=?, updated_at=CURRENT_TIMESTAMP WHERE url=?", (record_json(record), row["url"]))
        counts["events_enriched"] += 1
    connection.commit()
    return counts
