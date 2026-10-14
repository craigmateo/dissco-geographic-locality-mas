"""Find real specimen locality names to investigate for Issue #4."""

import json
from urllib.request import Request, urlopen
from urllib.parse import urlencode

API_URL = "https://sandbox.dissco.tech/api/digital-specimen/v1/search"

params = urlencode({"pageSize": 100, "pageNumber": 1})
request = Request(
    f"{API_URL}?{params}",
    headers={"User-Agent": "DiSSCo-Geographic-Locality-MAS/0.1"},
)

with urlopen(request, timeout=30) as response:
    data = json.load(response)

seen = set()
count = 0

for specimen in data.get("data", []):
    attributes = specimen.get("attributes", {})

    for event in attributes.get("ods:hasEvents", []):
        location = event.get("ods:hasLocation") or {}

        locality = location.get("dwc:locality")
        country = location.get("dwc:country")

        if not locality or not country:
            continue

        key = (locality.strip(), country.strip())

        if key in seen:
            continue

        seen.add(key)

        print(f"\nSpecimen: {specimen.get('id')}")
        print(f"Country: {country}")
        print(f"Locality: {locality}")

        count += 1
        if count >= 20:
            break

    if count >= 20:
        break

print(f"\nFound {count} distinct locality-country combinations.")
