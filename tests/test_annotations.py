"""Tests for the annotation mapping (community context -> openDS annotations)."""

import json

import pytest
from specimens import DEMO, digital_specimen

from geographic_locality_mas import annotations as an
from geographic_locality_mas.community_context import assess_location
from geographic_locality_mas.service import locations_from_specimen

AGENT = an.mas_agent("TEST/MAS-ID", "Geographic Locality MAS")
TIME = "2026-10-14T12:00:00.000Z"
REVIEW = "Review status: not reviewed by Sámi representatives."


def response_for(specimen):
    """A /v1/enrich-style response for a specimen."""
    _, locations = locations_from_specimen(specimen)
    return {"results": [{"event_index": loc["event_index"],
                         "target": an.location_path(loc["event_index"]), "location": loc,
                         "community_context": assess_location(loc)} for loc in locations]}


def annotate(*ids):
    specimen = digital_specimen(*ids)
    return an.to_annotations(specimen, response_for(specimen), AGENT, TIME)


def test_one_community_comment_per_location(gazetteers):
    anns = annotate(*DEMO)
    assert len(anns) == 3
    for i, a in enumerate(anns, start=1):
        assert a["oa:motivation"] == "oa:commenting"
        assert a["oa:hasTarget"]["oa:hasSelector"] == {
            "@type": "ods:ClassSelector",
            "ods:class": f"$['ods:hasEvents'][{i}]['ods:hasLocation']"}
        assert a["oa:hasTarget"]["dcterms:identifier"] == "https://doi.org/SANDBOX/X16-9NF-V0S"
        assert a["oa:hasBody"]["oa:value"][-2:] == ["Built without Sámi input.", REVIEW]
    assert "Synth-" not in json.dumps(anns, ensure_ascii=False)


def test_comment_tells_the_institution_whom_to_contact(gazetteers):
    body = annotate("KZJ-R72-SN2")[0]["oa:hasBody"]
    text = body["oa:value"]
    assert text[0].startswith("A Sámi community may be connected to this locality.")
    i = text.index("The holding institution, University of Oslo <https://ror.org/000000000>, "
                   "should contact, for collaboration and approval, in this order:")
    assert text[i + 1].startswith("1. Sámi Parliament of Norway")
    assert text[i + 2].startswith("2. Local Sámi community")
    assert body["dcterms:references"].startswith("https://www.regjeringen.no/")


def test_failed_register_lookup_fails_the_job(gazetteers):
    gazetteers.status["nls"] = 503
    with pytest.raises(an.CommunityContextError):
        annotate("1PD-GNZ-574")                      # Savukoski: no area, lookup failed


def test_specimen_without_location():
    specimen = {"dcterms:identifier": "SYN/0", "ods:hasEvents": [{}]}
    [a] = an.to_annotations(specimen, {"results": []}, AGENT, TIME)
    assert a["oa:hasTarget"]["oa:hasSelector"]["ods:class"] == "$['ods:hasEvents']"
    assert a["oa:hasBody"]["oa:value"][-1] == REVIEW
