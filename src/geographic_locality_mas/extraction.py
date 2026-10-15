"""Extract structured geographic context from DiSSCo specimen records."""
from .coord_extraction import extract_coordinates
from .dist_extraction import extract_distance

def extract_localities(specimen):
    attributes = specimen.get("attributes", {})
    results = []

    for event in attributes.get("ods:hasEvents", []):
        location = event.get("ods:hasLocation") or {}
        georef = location.get("ods:hasGeoreference") or {}

        if not location:
            continue

        if not georef.get("dwc:decimalLatitude") or not georef.get("dwc:decimalLongitude"):
            specimen_intermediate = {'locality': location.get("dwc:locality"), 'latitude': georef.get("dwc:decimalLatitude"), 'longitude': georef.get("dwc:decimalLongitude")}
            coordinates = extract_coordinates(specimen_intermediate)
            georef["dwc:decimalLatitude"] = coordinates.get("latitude")
            georef["dwc:decimalLongitude"] = coordinates.get("longitude")
        if not location.get("ods:hasDistance"):
            specimen_intermediate = {'locality': location.get("dwc:locality")}
            distance = extract_distance(specimen_intermediate)
            if "distance" in distance:
                location["distance"] = distance["distance"]

        results.append({
            "specimen_id": specimen.get("id"),
            "country": location.get("dwc:country"),
            "locality": location.get("dwc:locality"),
            "latitude": georef.get("dwc:decimalLatitude"),
            "longitude": georef.get("dwc:decimalLongitude"),
            "distance": location.get("distance")
        })

    return results