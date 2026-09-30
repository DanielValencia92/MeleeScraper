import csv
import json
from collections import Counter
from pathlib import Path

from .db import connect


def event_rows(db_path: Path) -> list[dict]:
    connection = connect(db_path)
    return [json.loads(row["payload_json"]) for row in connection.execute("SELECT payload_json FROM events ORDER BY url")]


def export_csv(db_path: Path, output_path: Path) -> int:
    rows = event_rows(db_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def quality_report(db_path: Path) -> dict:
    connection = connect(db_path)
    totals = dict(connection.execute("SELECT COUNT(*) AS discovered, SUM(status='ok') AS succeeded, SUM(status='failed') AS failed FROM discovered_urls").fetchone())
    rows = event_rows(db_path)
    total = len(rows)
    fields = ["name", "game", "format_raw", "city", "country", "player_count"]
    missing = {field: sum(not row.get(field) for row in rows) for field in fields}
    totals.update({"parsed_events": total, "missing": missing, "formats": dict(Counter(row["format_norm"] for row in rows))})
    return totals


def write_site_data(db_path: Path, site_dir: Path) -> tuple[int, dict]:
    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    rows = event_rows(db_path)
    summary = quality_report(db_path)
    (data_dir / "events.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (data_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return len(rows), summary

