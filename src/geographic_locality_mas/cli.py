"""Minimal command-line demonstration."""

import json
from pathlib import Path

from .extraction import extract_localities


def main():
    sample_path = Path(__file__).resolve().parents[2] / "data" / "sample-specimen.json"

    with sample_path.open(encoding="utf-8") as file:
        specimen = json.load(file)

    result = {
        "service": "geographic-locality-mas",
        "status": "extracted",
        "locations": extract_localities(specimen),
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
