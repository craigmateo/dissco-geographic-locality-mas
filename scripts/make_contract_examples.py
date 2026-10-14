"""Write the JSON examples for docs/value-service-contract.md.

  python scripts/make_contract_examples.py

Runs the value service in-process on one benchmark specimen (Vardø, SSR
263614: a Northern Sámi and a Kven name), with the gazetteer responses from
tests/fixtures (no network), and writes:
  docs/examples/enrich-request.json    what the MAS sends (POST /v1/enrich)
  docs/examples/enrich-response.json   what the value service returns
  docs/examples/annotations.json       what the MAS publishes (annotations.py)
Re-run after recording real fixtures (make_gazetteer_fixtures.py --record).
"""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from geographic_locality_mas import annotations as an
from geographic_locality_mas import indigenous_names as ina
from geographic_locality_mas.service import app

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "examples"
SPECIMEN_ID = "https://doi.org/SANDBOX/X16-9NF-V0S"


def specimen_from_benchmark(specimen_id):
    rec = next(r for r in json.loads((ROOT / "data" / "benchmark-indigenous.json")
                                     .read_text(encoding="utf-8"))
               if r["specimen_id"] == specimen_id)
    return {
        "@id": rec["specimen_id"],
        "@type": "ods:DigitalSpecimen",
        "dcterms:identifier": rec["specimen_id"],
        "ods:fdoType": "https://doi.org/21.T11148/894b1e6cad57e921764e",
        "ods:specimenName": rec["specimen_name"],
        "ods:organisationName": rec["organisation"],
        "ods:hasEvents": [{
            "@type": "ods:Event",
            "ods:hasLocation": {
                "@type": "ods:Location",
                "dwc:country": rec["country"],
                "dwc:county": rec["county"],
                "dwc:locality": rec["locality"],
                "ods:hasGeoreference": {
                    "@type": "ods:GeoReference",
                    "dwc:decimalLatitude": rec["latitude"],
                    "dwc:decimalLongitude": rec["longitude"],
                    "dwc:coordinateUncertaintyInMeters": rec["coordinate_uncertainty_m"],
                },
            },
        }],
    }


def write(name, data):
    path = OUT / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Wrote", path.relative_to(ROOT))


def main():
    sys.path.insert(0, str(ROOT / "tests"))
    from gazetteer_mocks import FakeGazetteers  # replays tests/fixtures, no network

    ina.SESSION = FakeGazetteers()
    ina.throttle = lambda host, rate: None
    OUT.mkdir(parents=True, exist_ok=True)
    specimen = specimen_from_benchmark(SPECIMEN_ID)
    request = {"specimen": specimen, "enrichments": ["indigenous_names"]}
    response = TestClient(app).post("/v1/enrich", json=request).json()
    agent = an.mas_agent("SANDBOX/MAS-ID", "Geographic Locality MAS")
    annotations = an.to_annotations(specimen, response, agent)
    write("enrich-request.json", request)
    write("enrich-response.json", response)
    write("annotations.json", {"jobId": "https://hdl.handle.net/SANDBOX/JOB-ID",
                               "annotations": annotations})


if __name__ == "__main__":
    main()
