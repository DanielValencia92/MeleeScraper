from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class EventRecord(BaseModel):
    source: str
    source_event_id: str
    url: HttpUrl
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    game: str | None = None
    format_raw: str | None = None
    format_norm: Literal["Premier", "Eternal", "Limited - Draft", "Limited - Sealed", "Limited - Other", "Unknown"] = "Unknown"
    event_tier: str | None = None
    organization: str | None = None
    venue: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    player_count: int | None = Field(default=None, ge=0)
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    crawled_at: datetime
    raw_snapshot_path: str

