"""Extract a geographically diverse sample of specimen localities."""

import argparse
import csv
import gzip
import json
import random
from collections import Counter
from pathlib import Path


def extract(input_path, output_path, limit=100, per_country=5):
    records = {}
    total = 0

    with gzip.open(input_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            specimen = json.loads(line)
            total += 1

            for event in specimen.get("ods:hasEvents", []):
                location = event.get("ods:hasLocation") or {}
                locality = location.get("dwc:locality")
                country = location.get("dwc:country")

                if not isinstance(locality, str) or not locality.strip():
                    continue

                locality = locality.strip()
                country = country.strip() if isinstance(country, str) else ""

                key = (country, locality)
                if key not in records:
                    records[key] = {
                        "specimen_doi": specimen.get("@id", ""),
                        "source_system": specimen.get("ods:sourceSystemName", ""),
                        "country": country,
                        "locality": locality,
                    }

    candidates = list(records.values())
    random.Random(42).shuffle(candidates)

    selected = []
    country_counts = Counter()

    for record in candidates:
        country = record["country"] or "(missing)"

        if country_counts[country] >= per_country:
            continue

        selected.append(record)
        country_counts[country] += 1

        if len(selected) >= limit:
            break

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["specimen_doi", "source_system", "country", "locality"],
        )
        writer.writeheader()
        writer.writerows(selected)

    print(f"Specimens scanned: {total:,}")
    print(f"Distinct locality-country combinations: {len(records):,}")
    print(f"Sample records written: {len(selected)}")
    print(f"Countries represented: {len(country_counts)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Path to .jsonl.gz dataset")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/locality_sample.csv"),
    )
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--per-country", type=int, default=5)
    args = parser.parse_args()

    extract(args.input, args.output, args.limit, args.per_country)
