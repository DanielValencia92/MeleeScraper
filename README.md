# SWU play analysis

A reproducible, public-data research pipeline for studying where Star Wars: Unlimited is played and whether high-tier event allocation matches local activity.

It deliberately uses direct HTTP requests rather than browser automation. It only stores public event-level information and saves raw responses so every parsed result can be audited or reparsed later.

## Setup

Use Python 3.11 or newer. The project target is 3.11 for broad compatibility.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## First collection

Discover public Star Wars: Unlimited events directly from Melee's browser-visible event search, then fetch, archive, and report on them:

```powershell
swu-play discover-melee --max-organizations 10 --from 2025-08-01 --to 2025-08-31
swu-play crawl --limit 100
swu-play report-quality
swu-play export data/exports/events.csv
swu-play serve
```

Start with `--max-organizations 10` to validate the results. The first run caches Melee's public organization directory, then scans a bounded number of organizations in descending activity order. It resumes from its SQLite queue in later runs. The adapter filters the public tournament listings to SWU and an optional inclusive date window; it does not use Melee's authenticated API or access participant-level information. Both discovery and crawling use Melee's published five-second crawl delay, archive the response body, and skip unchanged successful records on subsequent runs. Use `crawl --limit 100` for a bounded detail-page batch, or `--refresh` only when you deliberately want a new capture.

The generic parser records Open Graph, JSON-LD, page title, visible text, and public event URLs. The Melee discovery adapter is based on the same unauthenticated organization and tournament listings used by Melee's public pages. Do not add authenticated, private, or speculative endpoints.

## Local dashboard

`swu-play serve` rebuilds `site/data/events.json` and `site/data/summary.json`, then starts a local dashboard at [http://127.0.0.1:8000](http://127.0.0.1:8000). It only serves data from your local SQLite database; it does not perform collection itself.

```powershell
swu-play serve
```

Use `--port` to select another local port. Press `Ctrl+C` to stop the server. `build-site` remains available if you simply want to regenerate the dashboard JSON without starting a server. Raw captures and the SQLite database are ignored by default.

## Data boundaries

- Public event-level information only.
- No player profiles, participant lists, authentication, or private APIs.
- Missing values remain missing; the tool does not guess attendance or location.
- A player count is a player-entry count, not a unique-player estimate.
