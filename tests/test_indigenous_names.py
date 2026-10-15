"""Tests for geographic_locality_mas.indigenous_names, with HTTP mocked.

1. Benchmark: every record in data/benchmark-indigenous.json must come out as
   expected (match / nearby / no match) with the same place IDs, languages,
   name status and distances as in step 1.
2. Rules: Kven kept apart, address names skipped, rejected and historical
   names, ambiguity, missing or leaked keys, request parameters, paging.
3. No real Sámi or Kven names in the repo: the benchmark holds IDs only, the
   recorded responses hold made-up names (Synth-NNNN), and so do the tests.
"""

import json
import re

import pytest
from conftest import BENCHMARK, TEST_KEY, TODAY, as_location, short_id, ssr_entry
from gazetteer_mocks import FIXTURES, read_json

from geographic_locality_mas import indigenous_names as ina

RECORD = {short_id(r): r for r in BENCHMARK}
PLACEHOLDER = re.compile(r"Synth-\d{4}")    # made-up name in tests/fixtures
STATUSES = {"match", "nearby", "no_match", "no_coordinates", "not_covered", "error"}
MATCH_FIELDS = {"name", "language", "language_name", "language_category",
                "gazetteer_language", "name_status", "spelling_status", "gazetteer",
                "place_id", "place_uri", "name_id", "feature_type", "match_type",
                "matched_on", "distance_m", "score", "attribution", "licence", "caveats"}


def run(location, **kw):
    return ina.find_indigenous_names(location, today=TODAY, **kw)


def iso(languages):
    """' | '-joined gazetteer language values as ISO 639-3 codes."""
    return ina.join_unique(ina.language_info(v)[0] for v in (languages or "").split(" | "))


# ---- 1. Benchmark -----------------------------------------------------------------

@pytest.mark.parametrize("record", BENCHMARK, ids=short_id)
def test_benchmark_record(record, gazetteers):
    res = run(as_location(record))
    assert res["status"] == record["expected"].replace(" ", "_")
    assert res["gazetteer"] == record["gazetteer"]
    s = res["summary"]
    assert s["gazetteer_place_id"] == record["gazetteer_place_id"]
    assert s["nearest_distance_m"] == record["nearest_distance_m"]
    assert iso(s["parallel_language"]) == record["parallel_language"]
    assert (s["matched_name"] is None) == (record["matched_place_id"] is None)
    if record["expected"] == "match":
        assert ina.join_unique(m["language"] for m in res["matches"]) == record["parallel_language"]
        assert ina.join_unique(m["name_status"] for m in res["matches"]) == \
            record["parallel_name_status"]
        assert res["matches"][0]["place_id"] == record["gazetteer_place_id"]
        assert {m["place_id"] for m in res["matches"]} <= set(record["matched_place_id"].split(" | "))
        assert all(m["match_type"] == "name" for m in res["matches"])
        assert res["nearby"] == []
    else:
        assert res["matches"] == []
    if record["expected"] == "nearby":
        assert res["nearby"][0]["place_id"] == record["nearest_indigenous_place_id"]
        assert res["nearby"][0]["match_type"] == "proximity"
        assert res["nearby"][0]["matched_on"]["field"] == "coordinates"
    if record["expected"] == "no match":
        assert res["nearby"] == []
        assert record["nearest_indigenous_place_id"] is None


@pytest.mark.parametrize("record", BENCHMARK, ids=short_id)
def test_every_name_has_provenance(record, gazetteers):
    res = run(as_location(record))
    assert res["status"] in STATUSES
    assert res["query"]["url"].startswith(("https://ws.geonorge.no/", "https://avoin-"))
    for m in res["matches"] + res["nearby"] + res["minority_language_names"]:
        assert set(m) == MATCH_FIELDS
        assert re.fullmatch(r"[a-z]{3}", m["language"])          # ISO 639-3
        assert m["gazetteer"] == record["gazetteer"]
        assert 0 <= m["score"] <= 1
        assert m["licence"] == "https://creativecommons.org/licenses/by/4.0/"
        assert "CC BY 4.0" in m["attribution"]
        assert m["caveats"][0].startswith("Official name in a state gazetteer")
        assert "not community-sourced" in m["caveats"][0]
        if re.fullmatch(r"[0-9]+", m["place_id"]):
            assert m["place_uri"].endswith("/" + m["place_id"])
        else:
            assert m["place_uri"] is None                      # synthetic IDs


def test_name_match_example_kilpisjarvi(gazetteers):
    res = run(as_location(RECORD["3BZ-WFG-3PH"]))
    m = res["matches"][0]
    assert (m["language"], m["language_name"]) == ("sme", "Northern Sámi")
    assert PLACEHOLDER.fullmatch(m["name"])                  # made-up name, see section 3
    assert m["place_uri"] == "http://paikkatiedot.fi/so/1000772/10785565"
    assert m["matched_on"] == {"field": "locality", "text": "Kilpisjärvi",
                               "gazetteer_name": "Kilpisjärvi", "gazetteer_language": "fin"}
    assert m["score"] == 0.9
    assert m["attribution"].startswith("Contains data from the National Land Survey of "
                                       "Finland Geographic Names Register 10/2026")


def test_three_sami_languages_for_inari(gazetteers):
    res = run(as_location(RECORD["PK5-XNW-MZP"]))
    got = [(m["language"], m["language_name"]) for m in res["matches"]]
    assert got == [("smn", "Inari Sámi"), ("sme", "Northern Sámi"), ("sms", "Skolt Sámi")]
    assert len({m["name"] for m in res["matches"]}) == 3      # three different names
    # coordinate uncertainty unknown: says so
    assert any("uncertainty not recorded" in c for c in res["matches"][0]["caveats"])


def test_proximity_score_falls_with_distance(gazetteers):
    near = run(as_location(RECORD["980-0EE-4A0"]))["nearby"][0]    # 0 m
    far = run(as_location(RECORD["D0D-3FB-T12"]))["nearby"][0]     # 1238 m of 2000 m
    assert near["score"] == 0.5
    assert far["score"] == 0.19
    assert any("Proximity only" in c for c in far["caveats"])


# ---- 2. Rules -------------------------------------------------------------------------

def test_kven_kept_apart_from_sami(gazetteers):
    """Vardø (SSR 263614): the Northern Sámi name is a match, the Kven name is not."""
    res = run(as_location(RECORD["X16-9NF-V0S"]))
    assert [m["language"] for m in res["matches"]] == ["sme"]
    kven = res["minority_language_names"]
    assert [(k["language"], k["language_category"]) for k in kven] == [
        ("fkv", "national_minority")]
    assert any("national minority language" in c for c in kven[0]["caveats"])
    assert kven[0]["name"] not in json.dumps([res["matches"], res["nearby"]], ensure_ascii=False)


def test_kven_only_place_is_not_a_match(gazetteers):
    gazetteers.add("ssr", ssr_entry(69.7, 19.0, 2000, [
        (900001, "Elv", 300, [("Storelva", "Norsk", "hovednavn"),
                              ("Synth-kven-1", "Kvensk", "hovednavn")])]))
    res = run({"country": "Norway", "locality": "ved Storelva", "latitude": 69.7,
               "longitude": 19.0})
    assert res["status"] == "no_match"
    assert res["matches"] == [] and res["nearby"] == []
    assert [k["name"] for k in res["minority_language_names"]] == ["Synth-kven-1"]


def test_address_names_are_skipped(gazetteers):
    gazetteers.add("ssr", ssr_entry(69.65, 18.95, 2000, [
        (900002, "Adressenavn", 50, [("Storgata", "Norsk", "hovednavn"),
                                     ("Synth-street-1", "Nordsamisk", "hovednavn")])]))
    res = run({"country": "Norway", "locality": "Tromsø, Storgata 5", "latitude": 69.65,
               "longitude": 18.95})
    assert res["status"] == "no_match"
    assert res["summary"]["matched_name"] is None
    assert res["summary"]["n_names"] == 0


def test_names_without_spelling_are_ignored(gazetteers):
    gazetteers.add("ssr", ssr_entry(69.75, 22.0, 2000, [
        (900009, "Vann", 100, [(None, "Nordsamisk", "hovednavn")])]))
    res = run({"country": "Norway", "locality": "x", "latitude": 69.75, "longitude": 22.0})
    assert res["status"] == "no_match"
    assert res["summary"]["n_names"] == 0


def test_rejected_names_dropped_historical_flagged(gazetteers):
    gazetteers.add("ssr", ssr_entry(69.8, 23.0, 2000, [
        (900003, "Vann", 400, [("Langvatnet", "Norsk", "hovednavn"),
                               ("Synth-lake-1", "Nordsamisk", "historisk"),
                               ("Synth-lake-2", "Nordsamisk", "feilført")])]))
    res = run({"country": "Norway", "locality": "Langvatnet", "latitude": 69.8,
               "longitude": 23.0, "coordinate_uncertainty_m": 500})
    assert [m["name"] for m in res["matches"]] == ["Synth-lake-1"]
    m = res["matches"][0]
    assert m["score"] == 0.45
    assert any("not authorised for current public use" in c for c in m["caveats"])


def test_homonyms_with_different_sami_names_lower_the_score(gazetteers):
    gazetteers.add("ssr", ssr_entry(69.9, 24.0, 5000, [
        (900004, "Vann", 800, [("Storvatnet", "Norsk", "hovednavn"),
                               ("Synth-lake-3", "Nordsamisk", "hovednavn")]),
        (900005, "Vann", 3500, [("Storvatnet", "Norsk", "hovednavn"),
                                ("Synth-lake-4", "Nordsamisk", "hovednavn")])]))
    res = run({"country": "Norway", "locality": "Storvatnet", "latitude": 69.9,
               "longitude": 24.0, "coordinate_uncertainty_m": 5000})
    assert [m["place_id"] for m in res["matches"]] == ["900004"]   # nearest place
    assert res["matches"][0]["score"] == 0.45
    assert any("2 places named 'Storvatnet'" in c and "differ" in c
               for c in res["matches"][0]["caveats"])


def test_homonyms_beyond_the_uncertainty_do_not_compete(gazetteers):
    """Like Vardø: the town (360 m) and a tunnel that also carries the name (772 m)."""
    gazetteers.add("ssr", ssr_entry(70.0, 30.0, 2000, [
        (900010, "By", 360, [("Hamna", "Norsk", "hovednavn"),
                             ("Synth-town-1", "Nordsamisk", "hovednavn")]),
        (900011, "Tunnel", 772, [("Hamnatunnelen", "Norsk", "hovednavn"),
                                 ("Hamna", "Norsk", "hovednavn"),
                                 ("Synth-tunnel-1", "Nordsamisk", "hovednavn")])]))
    loc = {"country": "Norway", "locality": "Hamna by", "latitude": 70.0, "longitude": 30.0}
    precise = run({**loc, "coordinate_uncertainty_m": 707})["matches"][0]
    assert (precise["name"], precise["score"]) == ("Synth-town-1", 0.9)
    assert not any("places named" in c for c in precise["caveats"])
    vague = run({**loc, "coordinate_uncertainty_m": 1000})["matches"][0]
    assert vague["score"] == 0.45
    assert any("2 places named 'Hamna' within 1000 m" in c for c in vague["caveats"])


def test_locality_already_in_sami(gazetteers):
    gazetteers.add("ssr", ssr_entry(69.0, 23.05, 2000, [
        (900006, "Tettsted", 100, [("Testbygda", "Norsk", "hovednavn"),
                                   ("Synth-town-2", "Nordsamisk", "hovednavn")])]))
    res = run({"country": "NO", "locality": "Synth-town-2", "latitude": 69.0,
               "longitude": 23.05})
    assert res["status"] == "match"
    assert any("already uses this Indigenous name" in c for c in res["matches"][0]["caveats"])


def test_names_in_text_whole_words_and_unicode():
    names = [{"name": "Inari", "place_id": "1"}, {"name": "Synthá", "place_id": "2"},
             {"name": "Alta", "place_id": "3"}]
    decomposed = "Syntha\u0301 fell"   # á written as a + combining accent
    assert [h["name"] for h in ina.names_in_text(decomposed, names)] == ["Synthá"]
    assert ina.names_in_text("Inarijärvi", names) == []              # not a whole word
    assert [h["matched_text"] for h in ina.names_in_text("INARI village", names)] == ["INARI"]
    assert ina.names_in_text("Altenelven", names) == []
    assert ina.names_in_text(None, names) == []


def test_country_routing_and_not_covered(gazetteers):
    assert ina.gazetteer_for({"country": "Norway"}) == "ssr"
    assert ina.gazetteer_for({"country_code": "FI"}) == "nls"
    assert ina.gazetteer_for({"country": "Suomi"}) == "nls"
    res = run({"country": "Greece", "locality": "Milos", "latitude": 36.7, "longitude": 24.4})
    assert res["status"] == "not_covered"
    assert gazetteers.calls == []


def test_no_coordinates_makes_no_call(gazetteers):
    res = run({"country": "Finland", "county": "Enontekiö", "locality": "Kilpisjärvi"})
    assert res["status"] == "no_coordinates"
    assert res["gazetteer"] == "NLS Finland Geographic Names"
    assert gazetteers.calls == []


def test_request_parameters(gazetteers):
    run(as_location(RECORD["0DV-P9T-D6K"]))                 # uncertainty 10548 m
    url, params = gazetteers.calls[-1]
    assert url == "https://ws.geonorge.no/stedsnavn/v1/punkt"
    assert params["radius"] == 5000                          # SSR maximum
    assert params["koordsys"] == params["utkoordsys"] == 4258
    run(as_location(RECORD["X4B-BKF-T2X"]))                 # Finland, 100 km
    url, params = gazetteers.calls[-1]
    assert url == ina.MML_API
    assert params["api-key"] == TEST_KEY                     # sent to NLS ...
    assert params["bbox"] == ina.bbox_for(69.91, 27.02, 10000)


def test_key_never_in_results(gazetteers):
    ok = run(as_location(RECORD["3BZ-WFG-3PH"]))
    gazetteers.status["nls"] = 500
    failed = run(as_location(RECORD["3BZ-WFG-3PH"]))
    assert failed["status"] == "error"
    assert "HTTP 500" in failed["message"]
    for res in (ok, failed):                                  # ... but never returned
        text = json.dumps(res, ensure_ascii=False)
        assert TEST_KEY not in text
        assert re.search(r"api-key=(?!\*\*\*)", text) is None   # only as api-key=***


def test_missing_key(gazetteers, monkeypatch):
    monkeypatch.delenv("MML_API_KEY")
    res = run(as_location(RECORD["3BZ-WFG-3PH"]))
    assert res["status"] == "error"
    assert "MML_API_KEY is not set" in res["message"]
    assert gazetteers.calls == []


def test_ssr_paging(gazetteers):
    entry = ssr_entry(69.5, 25.0, 2000, [(900007, "Ås", 900, [("Bergåsen", "Norsk",
                                                               "hovednavn")])])
    page2 = ssr_entry(69.5, 25.0, 2000, [(900008, "Ås", 200, [("Synth-fell-1", "Nordsamisk",
                                                              "hovednavn")])])
    entry["pages"][0]["body"]["metadata"].update(totaltAntallTreff=2, viserTil=1)
    entry["pages"].append({"side": 2, "body": page2["pages"][0]["body"]})
    gazetteers.add("ssr", entry)
    res = run({"country": "Norway", "locality": "x", "latitude": 69.5, "longitude": 25.0})
    assert [p["side"] for _, p in gazetteers.calls] == [1, 2]
    assert res["nearby"][0]["name"] == "Synth-fell-1"      # sorted by distance


def test_nls_paging_follows_next_link(gazetteers):
    bbox = ina.bbox_for(68.5, 24.0, 2000)
    feature = {"type": "Feature", "id": "PN_1", "geometry": {"type": "Point",
               "coordinates": [24.0, 68.5]},
               "properties": {"placeId": 1, "spelling": "Synth-point-1", "language": "sme"}}
    gazetteers.add("nls", {"request": {"bbox": bbox}, "pages": [
        {"next": None, "body": {"features": [], "links": [
            {"rel": "next", "href": f"{ina.MML_API}?bbox={bbox}&next=abc%3D"}]}},
        {"next": "abc=", "body": {"features": [feature], "links": []}}]})
    res = run({"country": "Finland", "latitude": 68.5, "longitude": 24.0})
    assert [p.get("next") for _, p in gazetteers.calls] == [None, "abc="]
    assert res["status"] == "nearby"


def test_redact():
    assert ina.redact("https://x/items?bbox=1&api-key=abc123&limit=5") == \
        "https://x/items?bbox=1&api-key=***&limit=5"


def test_place_uris():
    assert ina.place_uri("263614", "ssr") == "https://stadnamn.kartverket.no/fakta/263614"
    assert ina.place_uri("P_10785565", "nls") == "http://paikkatiedot.fi/so/1000772/10785565"
    assert ina.place_uri("synthetic-1", "ssr") is None
    assert ina.place_uri(None, "nls") is None


# ---- 3. No real Sámi or Kven names in the repo ---------------------------------------
# Failure messages give counts only, so a real name never ends up in a CI log.

def protected_names(gaz, doc):
    """Every Sámi or Kven name in one fixture file."""
    for e in doc["entries"]:
        for p in e["pages"]:
            if gaz == "ssr":
                pairs = [(nm.get("skrivemåte"), nm.get("språk"))
                         for place in p["body"].get("navn") or []
                         for nm in place.get("stedsnavn") or []]
            else:
                props = [f.get("properties") or {} for f in p["body"].get("features") or []]
                pairs = [(pr.get("spelling") or pr.get("name"),
                          pr.get("language") or pr.get("languageCode")) for pr in props]
            yield from (n for n, lang in pairs if n and ina.language_info(lang)[2] != ina.OTHER)


@pytest.mark.parametrize("gaz", ["ssr", "nls"])
def test_fixtures_hold_only_made_up_sami_and_kven_names(gaz):
    names = list(protected_names(gaz, read_json(FIXTURES / f"gazetteer-{gaz}.json")))
    real = sum(not PLACEHOLDER.fullmatch(n) for n in names)
    assert names, f"no Sámi or Kven names in gazetteer-{gaz}.json"
    assert real == 0, f"{real} Sámi/Kven names in gazetteer-{gaz}.json are not made-up names"


def test_benchmark_holds_no_names():
    name_fields = {"matched_name", "indigenous_parallel", "nearest_indigenous_name"}
    assert not any(name_fields & set(r) for r in BENCHMARK)


def test_register_names_collects_every_sami_and_kven_name(gazetteers):
    rec = next(r for r in BENCHMARK if r["specimen_id"].endswith("X16-9NF-V0S"))
    register = set()
    with_names = ina.find_indigenous_names(as_location(rec), today=TODAY, register_names=register)
    assert with_names == ina.find_indigenous_names(as_location(rec), today=TODAY)   # unchanged
    listed = {r["name"] for k in ("matches", "minority_language_names", "nearby")
              for r in with_names[k]}
    assert listed <= register
    assert all(n.startswith("Synth-") for n in register)    # made-up Sámi/Kven names only
