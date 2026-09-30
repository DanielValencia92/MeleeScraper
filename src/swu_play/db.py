import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS discovered_urls (
    url TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    first_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    last_http_status INTEGER,
    content_hash TEXT,
    last_crawled_at TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS events (
    url TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_event_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS melee_organizations (
    organization_id INTEGER PRIMARY KEY,
    name TEXT,
    tournament_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    last_scanned_at TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS melee_venues (
    venue_id INTEGER PRIMARY KEY,
    name TEXT,
    city TEXT,
    region TEXT,
    country TEXT,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA)
    return connection
