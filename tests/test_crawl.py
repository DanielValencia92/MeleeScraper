from pathlib import Path

import pytest

from swu_play.crawl import crawl_pending, import_url_values


def test_crawl_limit_requires_positive_value(tmp_path: Path) -> None:
    import_url_values(tmp_path / "events.sqlite3", ["https://example.test/one"], "test")
    with pytest.raises(ValueError, match="at least one"):
        crawl_pending(tmp_path / "events.sqlite3", tmp_path / "raw", delay_seconds=1, limit=0)
