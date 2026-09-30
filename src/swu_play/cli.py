import json
import http.server
from datetime import date
from pathlib import Path
import socketserver

import httpx
import typer

from .crawl import crawl_pending, enrich_melee_venues, import_url_values, import_urls, reparse_archived
from .exports import export_csv, quality_report, write_hotbed_report, write_site_data
from .melee import MeleePublicDiscovery

app = typer.Typer(help="Collect and publish public SWU event research data.")
DEFAULT_DB = Path("data/swu_play.sqlite3")


@app.command()
def discover(url_file: Path, source: str = "manual-public-url", db: Path = DEFAULT_DB) -> None:
    """Import newline-separated public event URLs for a bounded collection run."""
    added, duplicate = import_urls(db, url_file, source)
    typer.echo(f"Imported {added} URLs; skipped {duplicate} duplicates.")


@app.command("discover-melee")
def discover_melee(
    max_organizations: int = 10,
    from_date: str | None = typer.Option(None, "--from"),
    to_date: str | None = typer.Option(None, "--to"),
    db: Path = DEFAULT_DB,
    delay: float = 5.0,
) -> None:
    """Find SWU events via Melee's public organization/tournament listings."""
    try:
        start = date.fromisoformat(from_date) if from_date else None
        end = date.fromisoformat(to_date) if to_date else None
    except ValueError as error:
        raise typer.BadParameter("Dates must use YYYY-MM-DD.") from error
    if start and end and start > end:
        raise typer.BadParameter("--from must not be after --to.")
    try:
        with MeleePublicDiscovery(delay) as discovery:
            result = discovery.discover(db, max_organizations, start, end)
    except (httpx.HTTPError, RuntimeError, ValueError) as error:
        raise typer.Exit(f"Melee discovery failed: {error}") from error
    added, duplicates = import_url_values(db, result.urls, "melee-public-organization-listing")
    typer.echo(f"Scanned {result.organizations_scanned} organizations; found {result.events_found} SWU events; imported {added}, skipped {duplicates} duplicates.")


@app.command()
def crawl(
    db: Path = DEFAULT_DB,
    raw_dir: Path = Path("data/raw"),
    delay: float = 5.0,
    refresh: bool = False,
    limit: int | None = typer.Option(None, "--limit", min=1),
) -> None:
    """Fetch pending public URLs and archive their HTML."""
    if delay < 1:
        raise typer.BadParameter("Use a delay of at least one second for respectful collection.")
    typer.echo(json.dumps(crawl_pending(db, raw_dir, delay, refresh, limit), indent=2))


@app.command()
def reparse(db: Path = DEFAULT_DB) -> None:
    """Rebuild records from saved HTML after improving a parser."""
    typer.echo(json.dumps(reparse_archived(db), indent=2))


@app.command("enrich-venues")
def enrich_venues(
    db: Path = DEFAULT_DB,
    delay: float = 5.0,
    limit: int | None = typer.Option(None, "--limit", min=1),
) -> None:
    """Add city/region/country from public Melee venue cards; no contact data is stored."""
    if delay < 5:
        raise typer.BadParameter("Melee's published crawl delay is five seconds.")
    typer.echo(json.dumps(enrich_melee_venues(db, delay, limit), indent=2))


@app.command("report-quality")
def report_quality(db: Path = DEFAULT_DB) -> None:
    """Print event completeness and parser coverage."""
    typer.echo(json.dumps(quality_report(db), indent=2))


@app.command()
def export(output: Path, db: Path = DEFAULT_DB) -> None:
    """Export normalized records to CSV."""
    typer.echo(f"Wrote {export_csv(db, output)} records to {output}.")


@app.command()
def analyze(
    output: Path = Path("data/reports/regional_hotbeds.md"),
    db: Path = DEFAULT_DB,
    min_events: int = typer.Option(2, "--min-events", min=1),
    top_cities: int = typer.Option(5, "--top-cities", min=1),
) -> None:
    """Write country → region → city hotbed rankings from the local dataset."""
    analysis = write_hotbed_report(db, output, min_events, top_cities)
    typer.echo(f"Wrote {len(analysis['countries'])} country summaries to {output}.")


@app.command("build-site")
def build_site(db: Path = DEFAULT_DB, site_dir: Path = Path("site")) -> None:
    """Build JSON consumed by the static local dashboard."""
    count, _ = write_site_data(db, site_dir)
    typer.echo(f"Wrote public dashboard data for {count} events to {site_dir / 'data'}.")


@app.command()
def serve(db: Path = DEFAULT_DB, site_dir: Path = Path("site"), port: int = 8000) -> None:
    """Build dashboard data and serve it locally until interrupted."""
    if not 1 <= port <= 65535:
        raise typer.BadParameter("Port must be between 1 and 65535.")
    count, _ = write_site_data(db, site_dir)
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(*args, directory=str(site_dir), **kwargs)
    with socketserver.ThreadingTCPServer(("127.0.0.1", port), handler) as server:
        typer.echo(f"Serving {count} events at http://127.0.0.1:{port} — press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            typer.echo("\nLocal dashboard stopped.")
