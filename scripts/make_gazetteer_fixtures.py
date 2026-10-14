"""Gazetteer responses for the tests, with made-up Sámi and Kven names.

The tests replay gazetteer responses instead of calling the APIs
(tests/fixtures/gazetteer-ssr.json, tests/fixtures/gazetteer-nls.json).
Each entry is one request (the same one find_indigenous_names() sends for a
benchmark record) and the response pages.

  python scripts/make_gazetteer_fixtures.py --record   # live, needs MML_API_KEY
  python scripts/make_gazetteer_fixtures.py            # offline, from the local recordings

Recording calls Kartverket SSR and NLS Finland and keeps only the fields the
module reads. The real responses go to output/fixtures-recorded/, which is
git-ignored: they stay on your computer. tests/fixtures/ gets the same
responses with every Sámi and Kven name replaced by a made-up name
(Synth-NNNN). The same name always gets the same placeholder, so name matching,
homonyms and scores behave exactly as with the real names. Names in other
languages that are spelled the same, or that contain such a name as a word
(e.g. a Swedish name for a site on a fell), get the placeholder too.

Why: Sámi place names are Sámi knowledge, also in a state gazetteer, and there
is no agreement yet to store or publish them. The API key is never written to
a file.
"""

import argparse
import copy
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from geographic_locality_mas import indigenous_names as ina

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "data" / "benchmark-indigenous.json"
FIXTURES = ROOT / "tests" / "fixtures"
RECORDED = ROOT / "output" / "fixtures-recorded"    # git-ignored: real names stay local
GAZ_OF = {"Kartverket SSR": "ssr", "NLS Finland Geographic Names": "nls"}

SSR_PLACE_KEYS = ["stedsnummer", "navneobjekttype", "meterFraPunkt", "stedstatus", "stedsnavn"]
SSR_NAME_KEYS = ["skrivemåte", "språk", "navnestatus", "skrivemåtestatus", "stedsnavnnummer"]
NLS_PROP_KEYS = ["placeId", "place_id", "placeNameId", "spelling", "name", "language",
                 "languageCode", "placeType", "placeTypeDescription", "languageOfficiality",
                 "languageOfficialStatus", "officialStatus", "languageDominance"]

NOTE_RECORDED = ("Real responses recorded by scripts/make_gazetteer_fixtures.py --record, "
                 "trimmed to the fields the module reads. Local only: never commit this file.")
NOTE_FIXTURES = ("Real responses recorded by scripts/make_gazetteer_fixtures.py --record, "
                 "trimmed to the fields the module reads, with every Sámi and Kven name "
                 "replaced by a made-up name (Synth-NNNN). The real recordings stay local "
                 "in output/fixtures-recorded/.")


def request_for(rec):
    """gazetteer, request key and search radius for one benchmark record."""
    gaz = GAZ_OF[rec["gazetteer"]]
    radius = ina.radius_for(rec["coordinate_uncertainty_m"],
                            max_m=ina.GAZETTEERS[gaz]["max_radius_m"])
    lat, lon = rec["latitude"], rec["longitude"]
    if gaz == "ssr":
        return gaz, {"nord": lat, "ost": lon, "radius": round(radius)}, radius
    return gaz, {"bbox": ina.bbox_for(lat, lon, radius)}, radius


# ---- recording ----------------------------------------------------------------------

def trim_ssr(body):
    navn = [{**{k: p.get(k) for k in SSR_PLACE_KEYS if k != "stedsnavn"},
             "stedsnavn": [{k: nm.get(k) for k in SSR_NAME_KEYS}
                           for nm in (p.get("stedsnavn") or [])]}
            for p in body.get("navn") or []]
    return {"metadata": body.get("metadata"), "navn": navn}


def trim_nls(body):
    features = [{"type": "Feature", "id": f.get("id"), "geometry": f.get("geometry"),
                 "properties": {k: v for k, v in (f.get("properties") or {}).items()
                                if k in NLS_PROP_KEYS}}
                for f in body.get("features") or []]
    token = ina.next_token(body)
    links = [{"rel": "next", "href": f"{ina.MML_API}?next={quote(token)}"}] if token else []
    return {"type": "FeatureCollection", "numberReturned": len(features), "links": links,
            "features": features}


def record_entry(gaz, req, max_pages=4):
    pages = []
    if gaz == "ssr":
        for side in range(1, max_pages + 1):
            body = ina.api_get(ina.SSR_API, "punkt", rate=2, nord=req["nord"], ost=req["ost"],
                               koordsys=4258, radius=req["radius"], utkoordsys=4258,
                               treffPerSide=500, side=side)
            pages.append({"side": side, "body": trim_ssr(body)})
            md = body.get("metadata") or {}
            if md.get("viserTil") is None or md["viserTil"] >= md.get("totaltAntallTreff", 0):
                break
        return pages
    key = os.environ.get("MML_API_KEY", "")
    token = None
    for _ in range(max_pages):
        params = {"bbox": req["bbox"], "limit": 1000, "api-key": key}
        if token:
            params["next"] = token
        body = ina.api_get(ina.MML_API, rate=2, **params)
        pages.append({"next": token, "body": trim_nls(body)})
        token = ina.next_token(body)
        if not token:
            break
    return pages


def build_recorded(records):
    out, seen = {"ssr": [], "nls": []}, {}
    for rec in records:
        gaz, req, _ = request_for(rec)
        key = (gaz, json.dumps(req, sort_keys=True))
        if key in seen:
            seen[key]["specimen_ids"].append(rec["specimen_id"])
            continue
        print("Recording", gaz, rec["specimen_id"], file=sys.stderr)
        entry = {"specimen_ids": [rec["specimen_id"]], "request": req,
                 "pages": record_entry(gaz, req)}
        seen[key] = entry
        out[gaz].append(entry)
    return out


# ---- made-up names --------------------------------------------------------------------

def name_fields(doc, gaz):
    """(dict holding the name, name key, language) for every name in a fixture document."""
    for e in doc["entries"]:
        for p in e["pages"]:
            if gaz == "ssr":
                for place in p["body"].get("navn") or []:
                    for nm in place.get("stedsnavn") or []:
                        yield nm, "skrivemåte", nm.get("språk")
            else:
                for f in p["body"].get("features") or []:
                    props = f.get("properties") or {}
                    field = "spelling" if "spelling" in props else "name"
                    yield props, field, props.get("language") or props.get("languageCode")


def placeholders_for(recorded):
    """Real name (NFC, casefolded) -> made-up name, for every Sámi and Kven name."""
    out = {}
    for gaz in ("ssr", "nls"):
        for holder, field, lang in name_fields(recorded[gaz], gaz):
            if holder.get(field) and ina.language_info(lang)[2] != ina.OTHER:
                out.setdefault(ina.nfc(holder[field]).casefold(), f"Synth-{len(out) + 1:04d}")
    return out


def replacer(placeholders, min_word=4, min_part=8):
    """made_up(text): the placeholder if the whole text is a Sámi or Kven name (in
    any language tag). Otherwise the text with such names replaced where they
    occur: names of >= min_part letters anywhere (also inflected, e.g. with a
    Finnish case ending), names of >= min_word letters as whole words."""
    def pattern(keys, word):
        keys = sorted(keys, key=len, reverse=True)
        if not keys:
            return None
        alt = "|".join(map(re.escape, keys))
        return re.compile(rf"\b({alt})\b" if word else f"({alt})", re.IGNORECASE)

    parts = pattern([k for k in placeholders if len(k) >= min_part], word=False)
    words = pattern([k for k in placeholders if min_word <= len(k) < min_part], word=True)

    def made_up(text):
        if not isinstance(text, str) or not text:
            return text
        text = ina.nfc(text)
        if text.casefold() in placeholders:
            return placeholders[text.casefold()]
        for p in (parts, words):
            if p is not None:
                text = p.sub(lambda m: placeholders.get(m.group(0).casefold(), m.group(0)), text)
        return text

    return made_up


def with_made_up_names(recorded):
    """Copies of the recorded documents with every Sámi and Kven name made up."""
    docs, placeholders = copy.deepcopy(recorded), placeholders_for(recorded)
    made_up = replacer(placeholders)
    for gaz in ("ssr", "nls"):
        for holder, field, _ in name_fields(docs[gaz], gaz):
            if holder.get(field):
                holder[field] = made_up(holder[field])
    out = {gaz: {"gazetteer": docs[gaz]["gazetteer"], "source": "recorded",
                 "names": "every Sámi and Kven name replaced with a made-up placeholder",
                 "created": docs[gaz]["created"], "note": NOTE_FIXTURES,
                 "attribution": docs[gaz]["attribution"], "entries": docs[gaz]["entries"]}
           for gaz in ("ssr", "nls")}
    return out, len(placeholders)


def write(path, doc):
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("Wrote", path.relative_to(ROOT), f"({len(doc['entries'])} requests)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--record", action="store_true",
                        help="call the live APIs (network, MML_API_KEY for Finland)")
    args = parser.parse_args()
    if args.record:
        if not os.environ.get("MML_API_KEY"):
            sys.exit("Set MML_API_KEY first (export MML_API_KEY=...).")
        records = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        today = datetime.now(timezone.utc).date()
        RECORDED.mkdir(parents=True, exist_ok=True)
        for gaz, entries in build_recorded(records).items():
            write(RECORDED / f"gazetteer-{gaz}.json", {
                "gazetteer": ina.GAZETTEERS[gaz]["label"], "source": "recorded",
                "created": today.isoformat(), "note": NOTE_RECORDED,
                "attribution": ina.attribution(gaz, today), "entries": entries})
    recorded = {}
    for gaz in ("ssr", "nls"):
        path = RECORDED / f"gazetteer-{gaz}.json"
        if not path.exists():
            sys.exit(f"No local recording {path.relative_to(ROOT)}: run with --record first.")
        recorded[gaz] = json.loads(path.read_text(encoding="utf-8"))
    docs, n = with_made_up_names(recorded)
    for gaz, doc in docs.items():
        write(FIXTURES / f"gazetteer-{gaz}.json", doc)
    print(f"{n} different Sámi and Kven names replaced with made-up names")


if __name__ == "__main__":
    main()
