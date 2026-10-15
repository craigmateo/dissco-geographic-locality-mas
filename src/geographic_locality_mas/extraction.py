"""Extract structured geographic context from DiSSCo specimen records."""

from .coord_extraction import extract_coordinates
from .dist_extraction import extract_distance


def extract_localities(specimen):
    attributes = specimen.get("attributes", {})
    results = []

    for event in attributes.get("ods:hasEvents", []):
        location = event.get("ods:hasLocation") or {}
        if not location:
            continue

        georef = location.get("ods:hasGeoreference") or {}
        locality = location.get("dwc:locality")
        latitude = georef.get("dwc:decimalLatitude")
        longitude = georef.get("dwc:decimalLongitude")

        # Extract missing coordinates without changing the source specimen.
        if latitude is None or longitude is None:
            coordinates = extract_coordinates({
                "locality": locality,
                "latitude": latitude,
                "longitude": longitude,
            })
            latitude = coordinates.get("latitude")
            longitude = coordinates.get("longitude")

        # Extract distance into a separate result, not the source location.
        distance = location.get("ods:hasDistance")
        if distance is None:
            extracted = extract_distance({"locality": locality})
            distance = extracted.get("distance")

        results.append({
            "specimen_id": specimen.get("id"),
            "country": location.get("dwc:country"),
            "locality": locality,
            "latitude": latitude,
            "longitude": longitude,
            "distance": distance,
        })

    return results
