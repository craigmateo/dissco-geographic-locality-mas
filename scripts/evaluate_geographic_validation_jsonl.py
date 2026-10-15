"""Evaluate geographic validation against a local gzipped JSONL dataset."""

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path

from geographic_locality_mas.extraction import extract_localities
from geographic_locality_mas.validation import (
    validate_coordinates_with_tolerance,
    suggest_coordinate_sign_corrections,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--tolerance-km", type=float, default=5.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/validation-jsonl-results.json"),
    )
    args = parser.parse_args()

    counts = Counter()
    reasons = Counter()
    source_counts = {}
    flagged = []
    specimens_processed = 0
    locations_processed = 0

    with gzip.open(args.input, "rt", encoding="utf-8") as stream:
        for line in stream:
            if specimens_processed >= args.limit:
                break

            raw = json.loads(line)
            specimen = {
                "id": raw.get("@id"),
                "attributes": raw,
            }
            source = raw.get("ods:sourceSystemName") or "Unknown"

            specimens_processed += 1

            if source not in source_counts:
                source_counts[source] = Counter()

            for locality in extract_localities(specimen):
                locations_processed += 1

                result = validate_coordinates_with_tolerance(
                    locality,
                    tolerance_km=args.tolerance_km,
                )

                status = result["status"]
                counts[status] += 1
                source_counts[source][status] += 1

                if result.get("reason"):
                    reasons[result["reason"]] += 1

                if status == "inconsistent":
                    suggestions = suggest_coordinate_sign_corrections(locality)

                    flagged.append({
                        **locality,
                        "source_system": source,
                        "boundary_distance_km": result["boundary_distance_km"],
                        "suggestions": suggestions,
                    })

            if specimens_processed % 100 == 0:
                print(f"\rProcessed {specimens_processed:,} specimens", end="", flush=True)

    report = {
        "specimens_processed": specimens_processed,
        "locations_processed": locations_processed,
        "tolerance_km": args.tolerance_km,
        "counts": dict(counts),
        "reasons": dict(reasons),
        "by_source_system": {
            source: dict(source_count)
            for source, source_count in source_counts.items()
        },
        "flagged": flagged,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\n\nEvaluation complete.")
    print("Specimens:", specimens_processed)
    print("Locations:", locations_processed)
    print("Validation counts:", dict(counts))
    print("Reasons:", dict(reasons))
    print("Flagged:", len(flagged))
    print("Report:", args.output)


if __name__ == "__main__":
    main()
