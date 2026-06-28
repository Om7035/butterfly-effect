"""Entity name normalization utilities."""


# Normalization mappings
ENTITY_NORMALIZATIONS: dict[str, str] = {
    # Federal Reserve
    "federal reserve": "Federal Reserve",
    "fed": "Federal Reserve",
    "fomc": "Federal Reserve",
    "federal open market committee": "Federal Reserve",
    "the fed": "Federal Reserve",
    # United States
    "united states": "United States",
    "us": "United States",
    "u.s.": "United States",
    "usa": "United States",
    "america": "United States",
    # Treasury
    "treasury": "US Treasury",
    "treasury department": "US Treasury",
    "us treasury": "US Treasury",
    # Other common entities
    "sec": "SEC",
    "securities and exchange commission": "SEC",
    "cpi": "Consumer Price Index",
    "consumer price index": "Consumer Price Index",
    "gdp": "GDP",
    "gross domestic product": "GDP",
    "unemployment": "Unemployment Rate",
    "unemployment rate": "Unemployment Rate",
}


def normalize_entity_name(name: str) -> str:
    """Normalize entity name to canonical form.

    Args:
        name: Raw entity name

    Returns:
        Normalized entity name
    """
    if not name:
        return name

    # Convert to lowercase for lookup
    lower_name = name.lower().strip()

    # Check if we have a normalization for this
    if lower_name in ENTITY_NORMALIZATIONS:
        return ENTITY_NORMALIZATIONS[lower_name]

    # Return original if no normalization found
    return name.strip()
