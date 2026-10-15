"""Tests for the value service (FastAPI), with gazetteer HTTP mocked."""

import json

import pytest
from conftest import TEST_KEY
from specimens import DEMO, digital_specimen

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from geographic_locality_mas.service import app, locations_from_specimen

REVIEW = "not reviewed by Sámi representatives"


@pytest.fixture
def client(gazetteers, monkeypatch):
    monkeypatch.delenv("VALUE_SERVICE_API_KEY", raising=False)
    return TestClient(app)


def enrich(client, **payload):
    resp = client.post("/v1/enrich", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["gazetteers"]["NLS Finland Geographic Names"] == "ready"


def test_enrich_specimen(client):
    body = enrich(client, specimen=digital_specimen(*DEMO))
    assert body["specimen_id"] == "https://doi.org/SANDBOX/X16-9NF-V0S"
    assert [r["event_index"] for r in body["results"]] == [1, 2, 3]   # event 0: no location
    vardo, karasjok, alta = body["results"]
    assert vardo["target"] == "$['ods:hasEvents'][1]['ods:hasLocation']"
    assert vardo["location"]["organisation"] == "University of Oslo"
    assert vardo["community_context"]["status"] == "indigenous_context"
    assert vardo["community_context"]["institution"]["name"] == "University of Oslo"
    assert [c["level"] for c in vardo["community_context"]["contacts"]] == ["national", "local"]
    assert karasjok["community_context"]["areas"][0]["unit"] == "Karasjok"
    assert alta["community_context"]["status"] == "no_known_context"


def test_no_names_and_review_status_everywhere(client):
    body = enrich(client, specimen=digital_specimen(*DEMO))
    assert "Synth-" not in json.dumps(body, ensure_ascii=False)       # never a name
    assert body["review_status"] == REVIEW
    for r in body["results"]:
        assert r["community_context"]["review_status"] == REVIEW
        assert r["community_context"]["comment"][-2] == "Built without Sámi input."
    empty = enrich(client, specimen={"ods:hasEvents": []})
    assert empty["review_status"] == REVIEW


def test_enrich_api_wrapper_and_locations_agree(client):
    bare = digital_specimen("KZJ-R72-SN2")
    a = enrich(client, specimen={"id": bare["@id"], "attributes": bare})
    b = enrich(client, locations=[a["results"][0]["location"]])
    assert a["results"][0]["community_context"] == b["results"][0]["community_context"]


def test_specimen_without_location(client):
    body = enrich(client, specimen={"dcterms:identifier": "https://doi.org/SANDBOX/L9L-8GD-0WM",
                                    "ods:hasEvents": [{"@type": "ods:Event"}]})
    assert body["results"] == []
    assert body["message"] == "No location in the specimen record."


@pytest.mark.parametrize("payload", [{}, {"specimen": {}, "locations": []},
                                     {"specimen": {}, "enrichments": ["indigenous_names"]}])
def test_bad_request(client, payload):
    assert client.post("/v1/enrich", json=payload).status_code == 422


def test_api_key_required_when_set(client, monkeypatch):
    monkeypatch.setenv("VALUE_SERVICE_API_KEY", "service-secret-123")
    payload = {"specimen": digital_specimen("980-0EE-4A0")}
    assert client.post("/v1/enrich", json=payload).status_code == 401
    wrong = {"Authorization": "Bearer nope"}
    assert client.post("/v1/enrich", json=payload, headers=wrong).status_code == 401
    right = {"Authorization": "Bearer service-secret-123"}
    assert client.post("/v1/enrich", json=payload, headers=right).status_code == 200


def test_nls_key_never_in_response(client, gazetteers):
    gazetteers.status["nls"] = 403
    body = enrich(client, specimen=digital_specimen("1PD-GNZ-574"))   # Savukoski: no area
    assert body["results"][0]["community_context"]["status"] == "error"
    assert TEST_KEY not in json.dumps(body)


def test_locations_from_specimen_reads_strings_as_numbers():
    _, locs = locations_from_specimen({"ods:organisationName": "Synthetic Museum",
                                       "ods:hasEvents": [{"ods:hasLocation": {
        "dwc:country": "Finland", "ods:hasGeoreference": {
            "dwc:decimalLatitude": "69.04", "dwc:decimalLongitude": "20.80"}}}]})
    assert (locs[0]["latitude"], locs[0]["longitude"]) == (69.04, 20.80)
    assert locs[0]["organisation"] == "Synthetic Museum"
