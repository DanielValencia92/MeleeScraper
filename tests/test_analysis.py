from swu_play.analysis import build_hotbed_analysis, render_hotbed_report


def test_hotbeds_group_city_variants_and_keep_zero_player_counts() -> None:
    records = [
        {"country": "US", "region": "TX", "city": "Austin", "player_count": 3, "format_norm": "Premier", "start_date": "2026-01-01"},
        {"country": "US", "region": "TX", "city": "austin ", "player_count": 0, "format_norm": "Premier", "start_date": "2026-01-02"},
        {"country": "US", "region": "OR", "city": "Portland", "player_count": 9, "format_norm": "Limited - Draft", "start_date": "2026-01-03"},
        {"country": None, "region": None, "city": None, "player_count": 2, "format_norm": "Premier"},
    ]
    analysis = build_hotbed_analysis(records, min_events=1, top_cities=5)
    texas = analysis["countries"][0]["regions"][0]
    assert analysis["events_with_city_and_country"] == 3
    assert texas["cities"][0]["city"] == "Austin"
    assert texas["cities"][0]["observed_events"] == 2
    assert texas["cities"][0]["enrolled_player_entries"] == 3
    assert "## US" in render_hotbed_report(analysis)
