


def extract_localities(specimen):
    attributes = specimen.get("attributes", {})
    results = []

    for event in attributes.get("ods:hasEvents", []):
        location = event.get("ods:hasLocation") or {}
        georef = location.get("ods:hasGeoreference") or {}

        if not location:
            continue

        results.append({
            "specimen_id": specimen.get("id"),
            "country": location.get("dwc:country"),
            "locality": location.get("dwc:locality"),
            "latitude": georef.get("dwc:decimalLatitude"),
            "longitude": georef.get("dwc:decimalLongitude"),
        })

    return results



