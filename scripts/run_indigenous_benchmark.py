"""Run find_indigenous_names() on every record of data/benchmark-indigenous.json.

  python scripts/run_indigenous_benchmark.py          # replay tests/fixtures, offline
  python scripts/run_indigenous_benchmark.py --live   # real APIs (MML_API_KEY for Finland)

Prints expected vs found status per record and writes all results to
output/indigenous-benchmark-python.json. The R twin
(R/02_run_indigenous_benchmark.R) runs the same records in R and compares its
results with this file: that is the R/Python parity check.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from geographic_locality_mas import indigenous_names as ina

ROOT = Path(__file__).resolve().parents[1]
LOCATION_KEYS = ["specimen_id", "event_index", "country", "county", "locality",
                 "latitude", "longitude", "coordinate_uncertainty_m"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="call the real gazetteer APIs")
    parser.add_argument("--today", help="YYYY-MM-DD for attribution dates (default: today)")
    args = parser.parse_args()
    if not args.live:
        sys.path.insert(0, str(ROOT / "tests"))
        from gazetteer_mocks import FakeGazetteers  # replays tests/fixtures

        ina.SESSION = FakeGazetteers()
        ina.throttle = lambda host, rate: None
        os.environ["MML_API_KEY"] = "replay-no-real-key"
    today = date.fromisoformat(args.today) if args.today else None
    records = json.loads((ROOT / "data" / "benchmark-indigenous.json").read_text(encoding="utf-8"))
    results, tally = [], Counter()
    for rec in records:
        res = ina.find_indigenous_names({k: rec.get(k) for k in LOCATION_KEYS}, today=today)
        results.append(res)
        expected, found = rec["expected"].replace(" ", "_"), res["status"]
        tally[(expected, found)] += 1
        names = ", ".join(f"{m['name']} ({m['language']})"
                          for m in res["matches"] or res["nearby"])
        flag = "ok  " if expected == found else "DIFF"
        print(f"{flag} {rec['specimen_id'].rsplit('/', 1)[-1]}  {expected:>8} -> {found:<14}"
              f"{names}")
    print("\n(expected, found): n")
    for (expected, found), n in sorted(tally.items()):
        print(f"  {expected:>8} -> {found:<14} {n}")
    out = ROOT / "output" / "indigenous-benchmark-python.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("Wrote", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
