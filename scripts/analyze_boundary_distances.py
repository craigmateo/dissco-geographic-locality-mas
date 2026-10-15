"""Measure distances from flagged specimens to country boundaries."""

import json
from pathlib import Path

from pyproj import CRS, Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

from geographic_locality_mas.extraction import extract_localities
from geographic_locality_mas.validation import validate_coordinates

ROOT = Path(__file__).resolve().parents[1]

specimens = json.loads(
    (ROOT / "data/validation-sample-1000.json").read_text(encoding="utf-8")
)

reference = json.loads(
    (ROOT / "data/reference/countries-10m.geojson").read_text(encoding="utf-8")
)

countries = {
    feature["properties"]["ADMIN"].casefold(): shape(feature["geometry"])
    for feature in reference["features"]
}

locations = [
    location
    for specimen in specimens
    for location in extract_localities(specimen)
]


def distance_to_country_km(latitude, longitude, polygon):
    """Approximate shortest ground distance to a country's boundary."""
    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} "
        "+datum=WGS84 +units=m +no_defs"
    )

    transformer = Transformer.from_crs(
        "EPSG:4326", local_crs, always_xy=True
    )

    projected_polygon = transform(transformer.transform, polygon)
    projected_point = transform(
        transformer.transform, Point(longitude, latitude)
    )

    return projected_point.distance(projected_polygon) / 1000


print("\nPotential inconsistencies and distances:\n")

for location in locations:
    result = validate_coordinates(location)

    if result["status"] != "inconsistent":
        continue

    country = location["country"]
    polygon = countries[country.strip().casefold()]

    distance = distance_to_country_km(
        location["latitude"],
        location["longitude"],
        polygon,
    )

    print(
        f"{country:20} "
        f"{distance:9.2f} km  "
        f"{location['specimen_id']}"
    )