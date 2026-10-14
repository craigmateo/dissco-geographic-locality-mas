"""Geographic validation of DiSSCo specimen records."""

import json
import math
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape

COUNTRIES_FILE = (
    Path(__file__).resolve().parents[2]
    / "data/reference/countries-10m.geojson"
)


@lru_cache(maxsize=1)
def load_countries():
    """Load country boundaries once and index them by country name."""
    with COUNTRIES_FILE.open(encoding="utf-8") as file:
        data = json.load(file)

    return {
        feature["properties"]["ADMIN"].casefold(): shape(feature["geometry"])
        for feature in data["features"]
    }


def validate_coordinates(specimen: dict) -> dict:
    """Check whether specimen coordinates fall inside its recorded country."""
    latitude = specimen.get("latitude")
    longitude = specimen.get("longitude")
    country = specimen.get("country")

    result = {
        "specimen_id": specimen.get("specimen_id"),
        "country": country,
        "latitude": latitude,
        "longitude": longitude,
        "status": "unable_to_validate",
        "reason": None,
    }

    if latitude is None or longitude is None:
        result["reason"] = "Missing latitude or longitude"
        return result

    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, (int, float))
        or not isinstance(longitude, (int, float))
        or not math.isfinite(latitude)
        or not math.isfinite(longitude)
    ):
        result["status"] = "invalid_coordinates"
        result["reason"] = "Coordinates must be finite numbers"
        return result

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        result["status"] = "invalid_coordinates"
        result["reason"] = "Coordinates outside valid geographic ranges"
        return result

    if not isinstance(country, str) or not country.strip():
        result["reason"] = "Missing country"
        return result

    countries = load_countries()
    boundary = countries.get(country.strip().casefold())

    if boundary is None:
        result["reason"] = "Country not found in reference dataset"
        return result

    point = Point(longitude, latitude)

    if boundary.covers(point):
        result["status"] = "consistent"
        result["reason"] = "Coordinates fall within recorded country"
    else:
        result["status"] = "inconsistent"
        result["reason"] = "Coordinates fall outside recorded country"

    return result
