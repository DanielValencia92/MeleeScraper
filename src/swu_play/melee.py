"""Discovery through Melee's public organization and tournament listings."""

import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import httpx

from .db import connect


BASE_URL = "https://melee.gg"
CRAWL_DELAY_SECONDS = 5.0
SWU_GAME_CODE = "StarWarsUnlimited"


@dataclass(frozen=True)
class MeleeDiscoveryResult:
    organizations_scanned: int
    events_found: int
    urls: list[str]


class MeleePublicDiscovery:
    """Use the same unauthenticated listing endpoints that Melee's public UI uses."""

    def __init__(self, delay_seconds: float = CRAWL_DELAY_SECONDS) -> None:
        if delay_seconds < CRAWL_DELAY_SECONDS:
            raise ValueError("Melee's robots.txt specifies a five-second crawl delay.")
        self.delay_seconds = delay_seconds
        self.http = httpx.Client(
            follow_redirects=True,
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

    def __enter__(self) -> "MeleePublicDiscovery":
        return self

    def __exit__(self, *args: object) -> None:
        self.http.close()

    def _post_table(self, path: str, start: int, length: int, sort_by_count: bool = False) -> dict:
        data: dict[str, str | int] = {"draw": 1, "start": start, "length": length}
        if sort_by_count:
            data.update({"order[0][column]": 0, "order[0][dir]": "desc"})
        response = self.http.post(f"{BASE_URL}{path}", data=data)
        response.raise_for_status()
        return response.json()

    def bootstrap_organizations(self, db_path: Path, page_size: int = 500) -> int:
        """Cache all public organizations once, preserving a resumable queue."""
        connection = connect(db_path)
        existing = connection.execute("SELECT COUNT(*) AS count FROM melee_organizations").fetchone()["count"]
        start = existing
        seen = existing
        while True:
            page = self._post_table("/Organization/GetOrganizations", start, page_size, sort_by_count=True)
            organizations = page.get("data", [])
            for organization in organizations:
                if not organization.get("ID"):
                    continue
                connection.execute(
                    "INSERT OR IGNORE INTO melee_organizations (organization_id, name, tournament_count) VALUES (?, ?, ?)",
                    (organization["ID"], organization.get("Name"), organization.get("TournamentCount", 0)),
                )
                seen += 1
            connection.commit()
            start += len(organizations)
            if start >= page.get("recordsFiltered", 0) or not organizations:
                return seen
            time.sleep(self.delay_seconds)

    def discover(self, db_path: Path, max_organizations: int, from_date: date | None, to_date: date | None) -> MeleeDiscoveryResult:
        if max_organizations < 1:
            raise ValueError("max-organizations must be at least one.")
        self.bootstrap_organizations(db_path)
        connection = connect(db_path)
        organizations = connection.execute(
            "SELECT organization_id FROM melee_organizations WHERE status = 'pending' ORDER BY tournament_count DESC, organization_id LIMIT ?",
            (max_organizations,),
        ).fetchall()
        urls: list[str] = []
        for index, organization in enumerate(organizations):
            organization_id = organization["organization_id"]
            try:
                response = self._post_table(f"/Hub/SearchOrganizationTournaments/{organization_id}", 0, 500)
                for event in response.get("data", []):
                    if event.get("Game") != SWU_GAME_CODE or not event.get("ID"):
                        continue
                    event_date = date.fromisoformat(event["StartDate"][:10])
                    if from_date and event_date < from_date:
                        continue
                    if to_date and event_date > to_date:
                        continue
                    urls.append(f"{BASE_URL}/Tournament/View/{event['ID']}")
                connection.execute(
                    "UPDATE melee_organizations SET status = 'scanned', last_scanned_at = CURRENT_TIMESTAMP, error = NULL WHERE organization_id = ?",
                    (organization_id,),
                )
            except (httpx.HTTPError, KeyError, ValueError) as error:
                connection.execute(
                    "UPDATE melee_organizations SET status = 'failed', last_scanned_at = CURRENT_TIMESTAMP, error = ? WHERE organization_id = ?",
                    (str(error)[:1000], organization_id),
                )
            connection.commit()
            if index < len(organizations) - 1:
                time.sleep(self.delay_seconds)
        return MeleeDiscoveryResult(len(organizations), len(urls), urls)
