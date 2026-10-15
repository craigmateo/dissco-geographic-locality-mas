"""Tests for community_context.py on synthetic locations (made-up names only)."""

import json
from pathlib import Path

import pytest

from conftest import BENCHMARK, as_location, short_id

from geographic_locality_mas.community_context import (
    assess_location,
    assert_no_names,
    community_comment,
    community_context,
    load_areas,
    load_contacts,
)

CASES = json.loads((Path(__file__).parent / "fixtures" / "community-cases.json")
                   .read_text(encoding="utf-8"))
EXPECTED = {
    "no-match-county": ("indigenous_context", 1),
    "no-nearby-municipality-and-merged-county": ("indigenous_context", 3),
    "fi-homeland-no-key": ("indigenous_context", 1),
    "fi-sodankyla-partial": ("indigenous_context", 1),
    "fi-outside-no-names": ("no_known_context", 0),
    "no-qc-inconsistent-county": ("indigenous_context", 1),
    "no-qc-inconsistent-nothing": ("not_assessed", 0),
    "sweden-not-covered": ("not_covered", 0),
    "no-lookup-error-tromso": ("error", 0),
    "no-no-coordinates-karasjok": ("indigenous_context", 1),
    "no-code-trondelag-german": ("indigenous_context", 1),
}


def run(case):
    cc = community_context(case["location"], qc_status=case["qc_status"],
                           names_result=case["names_result"])
    return cc, community_comment(cc)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_status_areas_and_text(case):
    cc, text = run(case)
    assert (cc["status"], len(cc["areas"])) == EXPECTED[case["id"]]
    assert assert_no_names(text, case["names_result"])
    assert "Synth-" not in json.dumps(cc) + "\n".join(text)        # never a name
    assert text[-1] == "Review status: not reviewed by Sámi representatives."
    if cc["status"] == "indigenous_context":
        assert [k["level"] for k in cc["contacts"]] == ["national", "local"]
        assert all(k["status"] for k in cc["contacts"])           # every contact says how sure
        assert cc["institution"]["status"] == "from the specimen record"
    else:
        assert cc["contacts"] == [] and cc["institution"] is None


def test_failed_coordinates_are_not_used():
    case = next(c for c in CASES if c["id"] == "no-qc-inconsistent-county")
    cc, text = run(case)
    assert cc["qc"]["coordinates_used"] is False and cc["evidence"] is None
    assert any(line.startswith("Coordinate check: inconsistent") for line in text)


def test_guard_stops_a_name():
    case = next(c for c in CASES if c["id"] == "no-match-county")
    with pytest.raises(ValueError) as err:
        assert_no_names(["Contact Synth-0001 first."], case["names_result"])
    assert "Synth" not in str(err.value)


def test_registry_rows_have_a_status():
    assert all(row["status"] for row in load_contacts())
    assert all(row["source_url"] and row["defined_by"] for row in load_areas())


def test_comment_is_addressed_to_the_institution():
    case = next(c for c in CASES if c["id"] == "no-match-county")
    _, text = run(case)
    i = text.index("The holding institution, Synthetic Herbarium <https://ror.org/000000000>, "
                   "should contact, for collaboration and approval, in this order:")
    assert text[i + 1].startswith("1. Sámi Parliament of Norway <https://sametinget.no/>")
    assert text[i + 2].startswith("2. Local Sámi community (to be designated by the Sámi side)")
    assert text[0] == ("A Sámi community may be connected to this locality. Before Sámi "
                       "knowledge is added to this record, the community needs to be "
                       "contacted for collaboration and approval.")


def test_unknown_institution():
    case = next(c for c in CASES if c["id"] == "fi-sodankyla-partial")    # no organisation
    _, text = run(case)
    assert "The holding institution should contact, for collaboration and approval, " \
           "in this order:" in text


# ---- assess_location(): the one call per location (MAS), registers mocked ---------------

RECORD = {short_id(r): r for r in BENCHMARK}


def demo_location(sid, **extra):
    return {**as_location(RECORD[sid]), "organisation": RECORD[sid]["organisation"], **extra}


def test_assess_location_on_the_demo_specimens(gazetteers):
    vardo, karasjok, alta = (assess_location(demo_location(s), qc_status="consistent")
                             for s in ("X16-9NF-V0S", "KZJ-R72-SN2", "KSS-ADF-LZD"))
    assert vardo["status"] == "indigenous_context" and vardo["areas"] == []   # register only
    assert vardo["evidence"]["status"] == "match" and vardo["evidence"]["languages"] == ["sme"]
    assert karasjok["status"] == "indigenous_context"
    assert karasjok["areas"][0]["unit"] == "Karasjok"
    assert alta["status"] == "no_known_context"
    for cc in (vardo, karasjok, alta):
        assert "Synth-" not in json.dumps(cc, ensure_ascii=False)          # never a name
        assert cc["comment"][-2:] == ["Built without Sámi input.",
                                      "Review status: not reviewed by Sámi representatives."]


def test_failed_check_or_no_key_means_no_register_lookup(gazetteers, monkeypatch):
    cc = assess_location(demo_location("KZJ-R72-SN2"), qc_status="inconsistent")
    assert cc["status"] == "indigenous_context" and cc["evidence"] is None  # area only
    assert gazetteers.calls == []
    monkeypatch.delenv("MML_API_KEY")
    cc = assess_location(demo_location("1PD-GNZ-574"), qc_status="consistent")
    assert cc["status"] == "not_assessed" and gazetteers.calls == []        # Finland, no key


def test_areas_only(gazetteers):
    cc = assess_location(demo_location("X16-9NF-V0S"), register_evidence=False)
    assert cc["status"] == "not_assessed" and gazetteers.calls == []


def test_names_the_record_itself_uses_are_allowed(gazetteers):
    # an institution named after a place: the comment repeats the record's own text
    location = demo_location("X16-9NF-V0S", organisation="Synth-0167 Museum")
    cc = assess_location(location)
    assert any("Synth-0167 Museum" in line for line in cc["comment"])
    names = {"matches": [{"name": "Synth-0167"}]}
    with pytest.raises(ValueError):
        assert_no_names(["Contact Synth-0167 first."], names, demo_location("X16-9NF-V0S"))
    assert assert_no_names(["Contact Synth-0167 first."], names, location)
