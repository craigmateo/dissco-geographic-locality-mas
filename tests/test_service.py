"""Tests for the value service (FastAPI), with gazetteer HTTP mocked."""

import json

import pytest
from conftest import BENCHMARK, TEST_KEY, as_location, short_id

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from geographic_locality_mas.service import app, locations_from_specimen

RECORD = {short_id(r): r for r in BENCHMARK}
FDO_TYPE = "https://doi.org/21.T11148/894b1e6cad57e921764e"


def digital_specimen(*records):
    """A bare openDS Digital Specimen (as RabbitMQ delivers it), one event per record."""
    events = [{"@type": "ods:Event"}]                 # event 0 has no location
    for r in records:
        events.append({"@type": "ods:Event", "ods:hasLocation": {
            "@type": "ods:Location", "dwc:country": r["country"], "dwc:county": r["county"],
            "dwc:locality": r["locality"],
            "ods:hasGeoreference": {
                "@type": "ods:GeoReference", "dwc:decimalLatitude": r["latitude"],
                "dwc:decimalLongitude": r["longitude"],
                "dwc:coordinateUncertaintyInMeters": r["coordinate_uncertainty_m"]}}})
    pid = records[0]["specimen_id"]
    return {"@id": pid, "dcterms:identifier": pid, "ods:fdoType": FDO_TYPE,
            "ods:hasEvents": events}


@pytest.fixture
def client(gazetteers, monkeypatch):
    monkeypatch.delenv("VALUE_SERVICE_API_KEY", raising=False)
    return TestClient(app)


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["gazetteers"]["NLS Finland Geographic Names"] == "ready"


def test_enrich_specimen(client):
    specimen = digital_specimen(RECORD["X16-9NF-V0S"], RECORD["KSS-ADF-LZD"])
    resp = client.post("/v1/enrich", json={"specimen": specimen})
    assert resp.status_code == 200
    body = resp.json()
    assert body["specimen_id"] == "https://doi.org/SANDBOX/X16-9NF-V0S"
    assert [r["event_index"] for r in body["results"]] == [1, 2]   # event 0: no location
    first, second = body["results"]
    assert first["target"] == "$['ods:hasEvents'][1]['ods:hasLocation']"
    assert first["indigenous_names"]["status"] == "match"
    assert first["indigenous_names"]["matches"][0]["language"] == "sme"
    assert first["indigenous_names"]["minority_language_names"][0]["language"] == "fkv"
    assert second["indigenous_names"]["status"] == "no_match"


def test_every_response_carries_the_review_status(client):
    specimen = digital_specimen(RECORD["X16-9NF-V0S"], RECORD["KSS-ADF-LZD"])
    body = client.post("/v1/enrich", json={"specimen": specimen}).json()
    assert body["review_status"] == "not reviewed by Sámi representatives"
    assert {r["indigenous_names"]["review_status"] for r in body["results"]} == {
        "not reviewed by Sámi representatives"}
    empty = client.post("/v1/enrich", json={"specimen": {"ods:hasEvents": []}}).json()
    assert empty["review_status"] == "not reviewed by Sámi representatives"


def test_enrich_api_wrapper_and_locations_agree(client):
    rec = RECORD["3BZ-WFG-3PH"]
    bare = digital_specimen(rec)
    wrapper = {"id": rec["specimen_id"], "attributes": bare}
    a = client.post("/v1/enrich", json={"specimen": wrapper}).json()
    b = client.post("/v1/enrich", json={"locations": [{**as_location(rec),
                                                        "event_index": 1}]}).json()
    assert a["results"][0]["indigenous_names"]["matches"] == \
        b["results"][0]["indigenous_names"]["matches"]
    assert a["results"][0]["indigenous_names"]["matches"][0]["place_id"] == "10785565"


def test_specimen_without_location(client):
    body = client.post("/v1/enrich", json={"specimen": {
        "dcterms:identifier": "https://doi.org/SANDBOX/L9L-8GD-0WM",
        "ods:hasEvents": [{"@type": "ods:Event"}]}}).json()
    assert body["results"] == []
    assert body["message"] == "No location in the specimen record."


@pytest.mark.parametrize("payload", [{}, {"specimen": {}, "locations": []}])
def test_bad_request(client, payload):
    assert client.post("/v1/enrich", json=payload).status_code == 422


def test_api_key_required_when_set(client, monkeypatch):
    monkeypatch.setenv("VALUE_SERVICE_API_KEY", "service-secret-123")
    payload = {"locations": [as_location(RECORD["980-0EE-4A0"])]}
    assert client.post("/v1/enrich", json=payload).status_code == 401
    wrong = {"Authorization": "Bearer nope"}
    assert client.post("/v1/enrich", json=payload, headers=wrong).status_code == 401
    right = {"Authorization": "Bearer service-secret-123"}
    assert client.post("/v1/enrich", json=payload, headers=right).status_code == 200


def test_nls_key_never_in_response(client, gazetteers):
    gazetteers.status["nls"] = 403
    body = client.post("/v1/enrich", json={"locations": [as_location(
        RECORD["E4W-B7Y-0J6"])]}).json()
    assert body["results"][0]["indigenous_names"]["status"] == "error"
    assert TEST_KEY not in json.dumps(body)


def test_locations_from_specimen_reads_strings_as_numbers():
    _, locs = locations_from_specimen({"ods:hasEvents": [{"ods:hasLocation": {
        "dwc:country": "Finland", "ods:hasGeoreference": {
            "dwc:decimalLatitude": "69.04", "dwc:decimalLongitude": "20.80"}}}]})
    assert (locs[0]["latitude"], locs[0]["longitude"]) == (69.04, 20.80)
