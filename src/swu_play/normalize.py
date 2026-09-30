def normalize_format(*values: str | None) -> str:
    """Classify explicit event-format labels without inferring from organizer text."""
    text = " ".join(value for value in values if value).casefold()
    if "eternal" in text:
        return "Eternal"
    if "draft" in text:
        return "Limited - Draft"
    if "sealed" in text:
        return "Limited - Sealed"
    if "limited" in text:
        return "Limited - Other"
    if "premier" in text:
        return "Premier"
    return "Unknown"
