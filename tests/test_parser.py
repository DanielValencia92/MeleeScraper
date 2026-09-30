from pathlib import Path

from swu_play.parser import parse_public_page, source_event_id


def test_parse_open_graph_title_and_format() -> None:
    html = '<html><head><meta property="og:title" content="SWU Eternal Weekly"><meta property="event:format" content="Eternal"></head><body>Star Wars Unlimited</body></html>'
    record = parse_public_page("https://example.test/events/123", html, Path("raw.html"), "test")
    assert record.name == "SWU Eternal Weekly"
    assert record.format_norm == "Eternal"
    assert record.game == "Star Wars: Unlimited"


def test_source_event_id_is_url_stable() -> None:
    assert source_event_id("https://example.test/events/123") == "events-123"
