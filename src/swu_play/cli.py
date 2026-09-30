import json
from pathlib import Path

import typer

from .crawl import crawl_pending, import_urls
from .exports import export_csv, quality_report, write_site_data

app = typer.Typer(help="Collect and publish public SWU event research data.")
DEFAULT_DB = Path("data/swu_play.sqlite3")


@app.command()
def discover(url_file: Path, source: str = "manual-public-url", db: Path = DEFAULT_DB) -> None:
    """Import newline-separated public event URLs for a bounded collection run."""
    added, duplicate = import_urls(db, url_file, source)
    typer.echo(f"Imported {added} URLs; skipped {duplicate} duplicates.")


@app.command()
def crawl(db: Path = DEFAULT_DB, raw_dir: Path = Path("data/raw"), delay: float = 2.5, refresh: bool = False) -> None:
    """Fetch pending public URLs and archive their HTML."""
    if delay < 1:
        raise typer.BadParameter("Use a delay of at least one second for respectful collection.")
    typer.echo(json.dumps(crawl_pending(db, raw_dir, delay, refresh), indent=2))


@app.command("report-quality")
def report_quality(db: Path = DEFAULT_DB) -> None:
    """Print event completeness and parser coverage."""
    typer.echo(json.dumps(quality_report(db), indent=2))


@app.command()
def export(output: Path, db: Path = DEFAULT_DB) -> None:
    """Export normalized records to CSV."""
    typer.echo(f"Wrote {export_csv(db, output)} records to {output}.")


@app.command("build-site")
def build_site(db: Path = DEFAULT_DB, site_dir: Path = Path("site")) -> None:
    """Build JSON consumed by the static GitHub Pages dashboard."""
    count, _ = write_site_data(db, site_dir)
    typer.echo(f"Wrote public dashboard data for {count} events to {site_dir / 'data'}.")

