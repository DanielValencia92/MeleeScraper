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

Discovery is intentionally source-agnostic in the first milestone. Put one public event URL per line in a text file, then import and fetch it:

```powershell
swu-play discover urls.txt
swu-play crawl
swu-play report-quality
swu-play export data/exports/events.csv
swu-play build-site
```

`crawl` uses a conservative default delay (2.5 seconds), retries transient failures, archives the response body, and skips unchanged successful records on subsequent runs. Use `--refresh` only when you deliberately want a new capture.

The generic parser records Open Graph, JSON-LD, page title, visible text, and public event URLs. A source-specific adapter may later extract stronger fields from stable public HTML or documented public feeds. Do not add authenticated, private, or speculative endpoints.

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
