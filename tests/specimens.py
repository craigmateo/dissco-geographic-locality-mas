"""Digital Specimens for tests, built from the benchmark (no network).

The benchmark records are real Sandbox specimens (IDs, admin fields, locality
text, coordinates); the gazetteer answers come from tests/fixtures, where every
Sámi and Kven name is made up (Synth-NNNN).
"""

from conftest import BENCHMARK, short_id

RECORD = {short_id(r): r for r in BENCHMARK}
FDO_TYPE = "https://doi.org/21.T11148/894b1e6cad57e921764e"
DEMO = ("X16-9NF-V0S", "KZJ-R72-SN2", "KSS-ADF-LZD")   # the MAS's three test specimens


def event(record):
    return {"@type": "ods:Event", "ods:hasLocation": {
        "@type": "ods:Location", "dwc:country": record["country"],
        "dwc:county": record["county"], "dwc:locality": record["locality"],
        "ods:hasGeoreference": {
            "@type": "ods:GeoReference", "dwc:decimalLatitude": record["latitude"],
            "dwc:decimalLongitude": record["longitude"],
            "dwc:coordinateUncertaintyInMeters": record["coordinate_uncertainty_m"]}}}


def digital_specimen(*ids):
    """A bare openDS Digital Specimen (as RabbitMQ delivers it): event 0 has no
    location, then one event per benchmark record."""
    records = [RECORD[i] for i in ids]
    pid = records[0]["specimen_id"]
    return {"@id": pid, "dcterms:identifier": pid, "ods:fdoType": FDO_TYPE,
            "ods:organisationName": records[0]["organisation"],
            "ods:organisationID": "https://ror.org/000000000",
            "ods:hasEvents": [{"@type": "ods:Event"}] + [event(r) for r in records]}
