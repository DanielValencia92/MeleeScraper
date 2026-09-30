from swu_play.melee import MeleeDiscoveryResult


def test_discovery_result_keeps_public_event_urls() -> None:
    result = MeleeDiscoveryResult(organizations_scanned=1, events_found=1, urls=["https://melee.gg/Tournament/View/123"])
    assert result.urls[0].endswith("/123")
    assert result.events_found == 1
