"""Transparent aggregations for the public event-level research dataset."""

from collections import Counter, defaultdict
from datetime import date
import re
import unicodedata


def _place_key(value: str | None) -> str:
    """Group superficial case/accent/whitespace variants without changing raw data."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"\s+", " ", text).strip().casefold()


def _label(values: Counter[str], fallback: str = "Unknown") -> str:
    return values.most_common(1)[0][0] if values else fallback


def _date_range(values: list[str]) -> tuple[str | None, str | None]:
    valid = sorted(value for value in values if _is_iso_date(value))
    return (valid[0], valid[-1]) if valid else (None, None)


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def build_hotbed_analysis(records: list[dict], min_events: int = 2, top_cities: int = 5) -> dict:
    """Aggregate observed events into country, region, and city-level hotbeds.

    A hotbed here means a concentration of *observed public listings*, not a
    measure of the entire player population or a causal claim about demand.
    """
    if min_events < 1 or top_cities < 1:
        raise ValueError("min_events and top_cities must be at least one.")
    country_groups: dict[str, dict] = {}
    located = 0
    for record in records:
        country, city = record.get("country"), record.get("city")
        if not country or not city:
            continue
        located += 1
        country_key, region_key, city_key = _place_key(country), _place_key(record.get("region")), _place_key(city)
        country_group = country_groups.setdefault(country_key, {"labels": Counter(), "records": [], "regions": {}})
        country_group["labels"][country] += 1
        country_group["records"].append(record)
        region_group = country_group["regions"].setdefault(region_key, {"labels": Counter(), "records": [], "cities": {}})
        region_group["labels"][record.get("region") or "Unknown"] += 1
        region_group["records"].append(record)
        city_group = region_group["cities"].setdefault(city_key, {"labels": Counter(), "records": []})
        city_group["labels"][city] += 1
        city_group["records"].append(record)

    def summarize(records_for_group: list[dict]) -> dict:
        formats = Counter(record.get("format_norm") or "Unknown" for record in records_for_group)
        starts, ends = _date_range([record.get("start_date") or "" for record in records_for_group])
        return {
            "observed_events": len(records_for_group),
            "enrolled_player_entries": sum(record.get("player_count") or 0 for record in records_for_group),
            "events_with_player_count": sum(record.get("player_count") is not None for record in records_for_group),
            "formats": dict(formats.most_common()),
            "first_event": starts,
            "last_event": ends,
        }

    countries = []
    for country_group in country_groups.values():
        regions = []
        for region_group in country_group["regions"].values():
            cities = []
            for city_group in region_group["cities"].values():
                city = {"city": _label(city_group["labels"]), **summarize(city_group["records"])}
                if city["observed_events"] >= min_events:
                    cities.append(city)
            cities.sort(key=lambda item: (-item["observed_events"], -item["enrolled_player_entries"], item["city"]))
            if cities:
                regions.append({"region": _label(region_group["labels"]), **summarize(region_group["records"]), "cities": cities[:top_cities]})
        regions.sort(key=lambda item: (-item["observed_events"], -item["enrolled_player_entries"], item["region"]))
        if regions:
            countries.append({"country": _label(country_group["labels"]), **summarize(country_group["records"]), "regions": regions})
    countries.sort(key=lambda item: (-item["observed_events"], -item["enrolled_player_entries"], item["country"]))
    return {
        "total_observed_events": len(records),
        "events_with_city_and_country": located,
        "events_without_city_or_country": len(records) - located,
        "min_events_per_city": min_events,
        "countries": countries,
    }


def render_hotbed_report(analysis: dict) -> str:
    lines = [
        "# Regional hotbeds from observed public Melee listings",
        "",
        "This ranks concentrations of observed public event listings. It is not a census of all play, a unique-player count, or evidence that one place has more demand than another. Enrolled counts are player-entries.",
        "",
        f"- Observed events: {analysis['total_observed_events']}",
        f"- Events with city and country: {analysis['events_with_city_and_country']}",
        f"- Events excluded for missing city or country: {analysis['events_without_city_or_country']}",
        f"- A city needs at least {analysis['min_events_per_city']} observed events to appear.",
    ]
    for country in analysis["countries"]:
        lines.extend(["", f"## {country['country']}", "", f"{country['observed_events']} observed events · {country['enrolled_player_entries']} enrolled player-entries"])
        for region in country["regions"]:
            lines.extend(["", f"### {region['region']}", "", "| City | Events | Player-entries | Leading formats |", "| --- | ---: | ---: | --- |"])
            for city in region["cities"]:
                formats = ", ".join(f"{name} ({count})" for name, count in list(city["formats"].items())[:3])
                lines.append(f"| {city['city']} | {city['observed_events']} | {city['enrolled_player_entries']} | {formats} |")
    return "\n".join(lines) + "\n"
