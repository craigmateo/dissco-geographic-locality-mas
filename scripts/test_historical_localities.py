"""Explore historical locality names using OpenStreetMap Nominatim.

Issue: https://github.com/craigmateo/dissco-geographic-locality-mas/issues/4
"""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://nominatim.openstreetmap.org/search"

LOCALITIES = [
    "Batavia, Indonesia",
    "Tapanoeli, Indonesia",
    "Tapanuli, Indonesia",
]


def search_locality(locality):
    params = urlencode({
        "q": locality,
        "format": "json",
        "namedetails": 1,
        "limit": 3,
    })

    request = Request(
        f"{API_URL}?{params}",
        headers={
            "User-Agent": "DiSSCo-Geographic-Locality-MAS/0.1 (educational prototype)"
        },
    )

    with urlopen(request, timeout=30) as response:
        return json.load(response)


def main():
    for locality in LOCALITIES:
        print(f"\nSearching: {locality}")

        try:
            results = search_locality(locality)

            if not results:
                print("  No matches found")
            else:
                for result in results:
                    names = result.get("namedetails", {})

                    print("  Place:", result.get("display_name"))
                    print("  Historical name:", names.get("old_name", "None"))
                    print("  Alternative name:", names.get("alt_name", "None"))

        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            print("  Lookup failed:", error)

        # Respect the public Nominatim service's rate limit.
        time.sleep(1.1)


if __name__ == "__main__":
    main()
