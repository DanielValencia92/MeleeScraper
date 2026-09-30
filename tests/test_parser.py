from pathlib import Path

from swu_play.parser import parse_public_page, source_event_id


def test_parse_open_graph_title_and_format() -> None:
    html = '<html><head><meta property="og:title" content="SWU Eternal Weekly"><meta property="event:format" content="Eternal"></head><body>Star Wars Unlimited</body></html>'
    record = parse_public_page("https://example.test/events/123", html, Path("raw.html"), "test")
    assert record.name == "SWU Eternal Weekly"
    assert record.format_norm == "Eternal"


def test_parse_melee_headline_uses_declared_format_not_organizer_name() -> None:
    html = '''<html><head><meta property="og:title" content="SWU Premier Weekly"></head><body>
      <p id="tournament-headline-start-date-field"><span data-value="2026-09-01T12:00:00Z"></span></p>
      <p id="tournament-headline-game">Game: STAR WARS: Unlimited</p>
      <p id="tournament-headline-organization">Organized by: <a>Eternal Games</a></p>
      Event Venue: <a data-type="venue" data-id="497">Eternal Games</a>
      <p id="tournament-headline-registration">Format: Premier | 12 of 128 Enrolled Players</p>
    </body></html>'''
    record = parse_public_page("https://melee.gg/Tournament/View/123", html, Path("raw.html"), "test")
    assert record.format_raw == "Premier"
    assert record.format_norm == "Premier"
    assert record.player_count == 12
    assert record.organization == "Eternal Games"
    assert record.venue == "Eternal Games"
    assert record.game == "Star Wars: Unlimited"


def test_source_event_id_is_url_stable() -> None:
    assert source_event_id("https://example.test/events/123") == "events-123"
