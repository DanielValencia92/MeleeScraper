from swu_play.normalize import normalize_format


def test_format_precedence_and_limited_variants() -> None:
    assert normalize_format("Eternal draft") == "Eternal"
    assert normalize_format("Weekly Draft") == "Limited - Draft"
    assert normalize_format("Premier Championship") == "Premier"
    assert normalize_format("Local event") == "Unknown"

