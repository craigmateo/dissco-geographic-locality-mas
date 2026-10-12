"""Fetch sample specimens from the DiSSCo Sandbox API."""

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from geographic_locality_mas.extraction import extract_localities

API_URL = "https://sandbox.dissco.tech/api/digital-specimen/v1/search"


def main():
    params = urlencode({"pageSize": 5, "pageNumber": 1})
    url = f"{API_URL}?{params}"

    print(f"Fetching specimens from {url}", file=sys.stderr)

    try:
        with urlopen(url, timeout=30) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"API request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    records = payload.get("data", [])

    result = {
        "source": API_URL,
        "specimens_retrieved": len(records),
        "locations": [
            location
            for specimen in records
            for location in extract_localities(specimen)
        ],
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
