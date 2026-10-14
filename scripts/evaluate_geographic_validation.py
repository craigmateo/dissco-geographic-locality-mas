"""Evaluate geographic validation on a sample of DiSSCo specimens."""

import json
import sys
from collections import Counter
from urllib.parse import urlencode
from urllib.request import urlopen
from pathlib import Path

from geographic_locality_mas.extraction import extract_localities
from geographic_locality_mas.validation import validate_coordinates

API_URL = "https://sandbox.dissco.tech/api/digital-specimen/v1/search"

PAGE_SIZE = 100
MAX_SPECIMENS = 1000
SAMPLE_FILE = Path("data/validation-sample-1000.json")


def fetch_specimens():
    """Load a cached specimen sample, or fetch and save it."""
    if SAMPLE_FILE.exists():
        print(f"Loading cached sample from {SAMPLE_FILE}", file=sys.stderr)
        with SAMPLE_FILE.open(encoding="utf-8") as file:
            return json.load(file)

    specimens = []

    for page in range(1, MAX_SPECIMENS // PAGE_SIZE + 1):
        params = urlencode({
            "pageSize": PAGE_SIZE,
            "pageNumber": page,
        })

        url = f"{API_URL}?{params}"
        print(f"Fetching page {page}...", file=sys.stderr)

        with urlopen(url, timeout=30) as response:
            payload = json.load(response)

        records = payload.get("data", [])
        specimens.extend(records)

        if len(records) < PAGE_SIZE:
            break

    SAMPLE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with SAMPLE_FILE.open("w", encoding="utf-8") as file:
        json.dump(specimens, file, indent=2, ensure_ascii=False)

    print(f"Saved {len(specimens)} specimens to {SAMPLE_FILE}", file=sys.stderr)

    return specimens


def main():
    specimens = fetch_specimens()

    locations = [
        location
        for specimen in specimens
        for location in extract_localities(specimen)
    ]

    results = [validate_coordinates(location) for location in locations]

    counts = Counter(result["status"] for result in results)
    total = len(results)

    print(f"\nSpecimens retrieved: {len(specimens)}")
    print(f"Locations evaluated: {total}")

    if total == 0:
        print("No locations available for validation.")
        return

    print("\nValidation results:")

    for status, count in counts.most_common():
        print(f"  {status}: {count} ({count / total:.1%})")

    validated = counts["consistent"] + counts["inconsistent"]

    if validated:
        print("\nAmong locations with valid coordinates and recognized countries:")
        print(f"  Consistent: {counts['consistent'] / validated:.1%}")
        print(f"  Inconsistent: {counts['inconsistent'] / validated:.1%}")

    print("\nPotential geographic inconsistencies:")

    for location, result in zip(locations, results):
        if result["status"] == "inconsistent":
            print(
                f"  {location['specimen_id']} | "
                f"{location['country']} | "
                f"{location['latitude']}, {location['longitude']}"
            )


if __name__ == "__main__":
    main()