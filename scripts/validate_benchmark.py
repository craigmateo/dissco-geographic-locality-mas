"""Validate benchmark specimens and summarize the results."""

import json
from collections import Counter
from pathlib import Path

from geographic_locality_mas.validation import validate_coordinates

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark-10.json"

with BENCHMARK.open(encoding="utf-8") as file:
    specimens = json.load(file)

results = [validate_coordinates(specimen) for specimen in specimens]

print(f"\nSpecimens evaluated: {len(results)}")
print("\nValidation results:")

for status, count in Counter(r["status"] for r in results).items():
    print(f"  {status}: {count} ({count / len(results):.1%})")

print("\nIndividual records:")

for specimen, result in zip(specimens, results):
    country = specimen.get("country") or "Unknown"
    locality = specimen.get("locality") or "No locality"

    print(
        f"{result['status']:20} "
        f"{country:20} "
        f"{locality}"
    )