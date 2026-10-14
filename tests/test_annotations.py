"""Tests for the annotation mapping (value-service result -> openDS annotations)."""

import json

import pytest
from conftest import BENCHMARK, TODAY, as_location, short_id

from geographic_locality_mas import annotations as an
from geographic_locality_mas.indigenous_names import find_indigenous_names

RECORD = {short_id(r): r for r in BENCHMARK}
AGENT = an.mas_agent("TEST/MAS-ID", "Geographic Locality MAS")
TIME = "2026-10-14T12:00:00.000Z"
SPECIMEN = {"dcterms:identifier": "https://doi.org/SANDBOX/X16-9NF-V0S",
            "ods:fdoType": "https://doi.org/21.T11148/894b1e6cad57e921764e"}


def response_for(*ids):
    """A /v1/enrich-style response for benchmark records (one event each)."""
    results = []
    for i, sid in enumerate(ids):
        loc = {**as_location(RECORD[sid]), "event_index": i}
        results.append({"event_index": i, "target": an.location_path(i), "location": loc,
                        "indigenous_names": find_indigenous_names(loc, today=TODAY)})
    return {"results": results}


def annotate(*ids, **kw):
    return an.to_annotations(SPECIMEN, response_for(*ids), AGENT, TIME, **kw)


def test_match_becomes_one_entity_relationship_per_place(gazetteers):
    anns = annotate("PK5-XNW-MZP")                 # Inari: 3 Sámi names, 1 place
    assert len(anns) == 1
    a = anns[0]
    assert a["oa:motivation"] == "ods:adding"
    assert a["oa:hasTarget"]["oa:hasSelector"] == {"@type": "ods:ClassSelector",
                                                   "ods:class": "$['ods:hasEntityRelationships']"}
    assert a["oa:hasTarget"]["dcterms:identifier"] == SPECIMEN["dcterms:identifier"]
    assert a["oa:hasBody"]["ods:score"] == 0.9
    assert a["oa:hasBody"]["dcterms:references"].startswith("https://avoin-paikkatieto")
    er = json.loads(a["oa:hasBody"]["oa:value"][0])
    assert er["@type"] == "ods:EntityRelationship"
    assert er["dwc:relationshipOfResource"] == "hasIndigenousPlaceName"
    assert er["ods:relatedResourceURI"] == "http://paikkatiedot.fi/so/1000772/10818625"
    assert er["dwc:relationshipEstablishedDate"] == TIME
    remarks = er["dwc:relationshipRemarks"]
    for text in ["(Inari Sámi, smn", "(Northern Sámi, sme", "(Skolt Sámi, sms",
                 "NLS Finland Geographic Names, place 10818625", "locality text 'Inari'",
                 "not community-sourced", "CC BY 4.0",
                 "Review status: not reviewed by Sámi representatives."]:
        assert text in remarks


def test_two_places_two_relationships(gazetteers):
    anns = annotate("Y34-C6Y-2RX")                 # "Kilpisjärvi, Saana"
    uris = [json.loads(a["oa:hasBody"]["oa:value"][0])["ods:relatedResourceURI"] for a in anns]
    assert uris == ["http://paikkatiedot.fi/so/1000772/10785524",
                    "http://paikkatiedot.fi/so/1000772/10785565"]


def test_kven_is_not_annotated(gazetteers):
    response = response_for("X16-9NF-V0S")         # Vardø: a Northern Sámi and a Kven name
    kven = response["results"][0]["indigenous_names"]["minority_language_names"][0]["name"]
    anns = an.to_annotations(SPECIMEN, response, AGENT, TIME)
    assert len(anns) == 1
    remarks = json.loads(anns[0]["oa:hasBody"]["oa:value"][0])["dwc:relationshipRemarks"]
    assert "(Northern Sámi, sme; name status hovednavn)" in remarks
    assert kven not in json.dumps(anns, ensure_ascii=False)


def test_nearby_becomes_a_comment_on_the_location(gazetteers):
    anns = annotate("KSS-ADF-LZD", "980-0EE-4A0")  # event 0 no match, event 1 nearby
    assert [a["oa:motivation"] for a in anns] == ["oa:commenting", "oa:commenting"]
    paths = [a["oa:hasTarget"]["oa:hasSelector"]["ods:class"] for a in anns]
    assert paths == ["$['ods:hasEvents'][0]['ods:hasLocation']",
                     "$['ods:hasEvents'][1]['ods:hasLocation']"]
    assert "ods:score" not in anns[0]["oa:hasBody"]
    nearby = anns[1]["oa:hasBody"]
    assert nearby["ods:score"] == 0.5
    assert "(Northern Sámi, sme" in nearby["oa:value"][0]


def test_no_location_comment():
    anns = an.to_annotations(SPECIMEN, {"results": []}, AGENT, TIME)
    assert anns[0]["oa:motivation"] == "oa:commenting"
    assert anns[0]["oa:hasTarget"]["oa:hasSelector"]["ods:class"] == "$['ods:hasEvents']"


def test_low_score_is_a_comment_not_a_relationship(gazetteers):
    anns = annotate("3BZ-WFG-3PH", min_score=0.95)
    assert [a["oa:motivation"] for a in anns] == ["oa:commenting"]
    assert "Low-confidence match (score 0.9" in anns[0]["oa:hasBody"]["oa:value"][0]


def test_lookup_error_raises(gazetteers):
    gazetteers.status["ssr"] = 500
    with pytest.raises(an.IndigenousNamesError, match="HTTP 500"):
        annotate("YE8-RMJ-LM2")


def test_every_annotation_carries_the_review_status(gazetteers):
    anns = annotate("PK5-XNW-MZP", "KSS-ADF-LZD", "980-0EE-4A0")   # match, no match, nearby
    anns += an.to_annotations(SPECIMEN, {"results": []}, AGENT, TIME)
    assert len(anns) == 4
    for a in anns:
        text = a["oa:hasBody"]["oa:value"][0]
        assert "Review status: not reviewed by Sámi representatives." in text


def test_not_covered_comment_can_be_switched_off():
    res = {"results": [{"event_index": 0, "indigenous_names": find_indigenous_names(
        {"country": "Greece", "locality": "Milos"}, today=TODAY)}]}
    assert len(an.to_annotations(SPECIMEN, res, AGENT, TIME)) == 1
    assert an.to_annotations(SPECIMEN, res, AGENT, TIME,
                             comment_on=("nearby", "no_match")) == []
