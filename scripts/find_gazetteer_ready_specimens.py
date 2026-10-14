"""Find DiSSCo Sandbox specimens that are good test cases for Indigenous place names.

DiSSCo MAS Hackathon 2026 - Geographic Place Names team.
Workstream: Indigenous place names.

Python twin of the R script 01_find_gazetteer_ready_specimens.R, which is kept
outside this repo. Same sections, same function names, same outputs, so the two
can be read side by side.

Step 1 looks for specimen records that have
  (a) usable locality data (coordinates, or a clean place name + admin units)
  (b) a location covered by an authoritative gazetteer that holds
      Indigenous-language names with language tags and provenance.

Sections ("# %%" cells: run one at a time in VS Code or Positron):
  0. Setup and helpers
  1. Survey: where is the georeferenced Sandbox data?
  2. Pull candidate specimens for one region (default: Sapmi, NO + FI)
  3. Gazetteer hit test (Kartverket SSR for Norway, NLS for Finland)
  4. Save the benchmark: IDs only in data/ (for the repo), names only in output/

Run from the repo root:
  make setup
  .venv/bin/pip install -e ".[explore]"      # adds requests + pandas
  .venv/bin/python -i scripts/find_gazetteer_ready_specimens.py
(-i keeps Python open afterwards, so you can look at survey, cand, summ_no ...)

Finland needs MML_API_KEY, a free key from the National Land Survey of Finland.
The script reads it from the environment, from .env in the repo root
(git-ignored) or from ~/.Renviron, so the R and Python versions share one key.

API notes (from the DiSSCo backend source, dissco-core-backend):
- Search filters: country, countryCode, locality, organisationName,
  datasetName, ... (exact match, case-sensitive) or with * (wildcard,
  case-insensitive). q = Elasticsearch query_string (field ranges work).
- hasLatitude / hasLocality / hasCountry = true|false (field exists).
  Do NOT use hasLongitude: the backend maps it to hasLocality (bug).
- Different keys are ANDed. Repeating a key ORs (country=A&country=B).
- Paging stops at 10,000 hits (pageNumber x pageSize). Narrow the query.
- /aggregation returns only the top 10 buckets per facet and rejects pageSize.
- Unknown parameters return HTTP 400.
"""

# %% 0. Setup and helpers ------------------------------------------------------

import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from geographic_locality_mas.indigenous_names import (
    GazetteerError,
    join_unique,
    language_info,
    mml_near,
    radius_for,
    ssr_near,
    summarise_hits,
)

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 60)

# Repo root, wherever you start Python (cells fall back to the working directory)
ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
DATA = ROOT / "data"
OUTPUT = ROOT / "output"
DATA.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

DS_API = "https://sandbox.dissco.tech/api/digital-specimen/v1"


def read_key(name, files):
    """Key from the environment, else from KEY=value lines in env files.

    R reads ~/.Renviron by itself. Python needs this small helper.
    """
    if os.environ.get(name):
        return os.environ[name]
    for path in files:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                key, sep, value = line.strip().partition("=")
                if sep and key.strip() == name:
                    return value.strip().strip("\"'")
    return ""


MML_API_KEY = read_key("MML_API_KEY", [ROOT / ".env", Path.home() / ".Renviron"])
if MML_API_KEY:                    # the package reads the key from the environment only
    os.environ.setdefault("MML_API_KEY", MML_API_KEY)


def first(x):
    """First element as text, None if missing. R: chr1()."""
    if isinstance(x, list):
        return first(x[0]) if x else None
    return None if x is None else str(x)


def count(df, *cols, sort=False):
    """Rows per group. R: dplyr::count()."""
    out = df.groupby(list(cols), dropna=False).size().reset_index(name="n")
    return out.sort_values("n", ascending=False) if sort else out


SESSION = requests.Session()
SESSION.headers["User-Agent"] = "DiSSCo MAS hackathon - Geographic Place Names team"
_LAST_CALL = {}


def api_get(url, path=None, rate=5, **params):
    """GET a JSON API and return the parsed body (dicts and lists).

    R: api_get() with httr2. A list value becomes a repeated key
    (country=["A", "B"] -> country=A&country=B), like .multi = "explode".
    """
    if path:
        url = f"{url}/{path}"
    host = url.split("/")[2]
    for attempt in range(3):                         # R: req_retry(max_tries = 3)
        wait = 1 / rate - (time.monotonic() - _LAST_CALL.get(host, -1e9))
        if wait > 0:                                 # R: req_throttle(rate = rate)
            time.sleep(wait)
        resp = SESSION.get(url, params=params, timeout=60)
        _LAST_CALL[host] = time.monotonic()
        if resp.status_code in (429, 503) and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        if not resp.ok:                              # R: req_error(body = ...)
            raise requests.HTTPError(
                f"HTTP {resp.status_code} for {resp.url}: {resp.text[:300]}",
                response=resp,
            )
        return resp.json()


def ds_get(path, **params):
    return api_get(DS_API, path, **params)


def ds_count(**params):
    """Number of matching specimens (reads meta.totalRecords, downloads 1 record)."""
    return ds_get("search", pageSize=1, **params)["meta"]["totalRecords"]


def ds_agg(**params):
    """Top-10 buckets per facet: country, organisationName, datasetName, ..."""
    attributes = ds_get("aggregation", **params)["data"]["attributes"]
    rows = [{"term": term, "value": value, "n": n}
            for term, buckets in attributes.items()
            for value, n in buckets.items()]
    return pd.DataFrame(rows, columns=["term", "value", "n"])


def ds_values(term, prefix):
    """Values of one field starting with a prefix (case-insensitive), with counts.

    Useful for messy strings, e.g. ds_values("country", "New")
    """
    res = ds_get("searchTermValue", term=term, value=prefix)
    buckets = res["data"]["attributes"].get(term) or {}
    return pd.DataFrame(list(buckets.items()), columns=["value", "n"])


def ds_search(n_max=1000, page_size=100, **params):
    """Page through search results. Returns a list of specimen objects."""
    out, page = [], 1
    while True:
        res = ds_get("search", pageSize=page_size, pageNumber=page, **params)
        data = res.get("data") or []
        out.extend(data)
        if not data or not (res.get("links") or {}).get("next") or len(out) >= n_max:
            break
        if (page + 1) * page_size > 10000:
            print("Stopping at the 10,000-hit paging limit. Narrow the query.")
            break
        page += 1
    return out[:n_max]


# One row per specimen x event, with the location fields we care about
LOC_FIELDS = ["dwc:country", "dwc:countryCode", "dwc:stateProvince",
              "dwc:county", "dwc:municipality", "dwc:locality",
              "dwc:verbatimLocality", "dwc:higherGeography", "dwc:island",
              "dwc:waterBody", "dwc:locationID"]
GEO_FIELDS = ["dwc:decimalLatitude", "dwc:decimalLongitude",
              "dwc:coordinateUncertaintyInMeters", "dwc:geodeticDatum"]
LOC_COLUMNS = (["specimen_id", "event_index", "specimen_name", "organisation", "dataset"]
               + [f.removeprefix("dwc:") for f in LOC_FIELDS + GEO_FIELDS])


def flatten_locations(specimens):
    rows = []
    for s in specimens:
        a = s.get("attributes") or {}
        events = a.get("ods:hasEvents") or [{}]
        for i, ev in enumerate(events):        # i is 0-based, as in $['ods:hasEvents'][i]
            loc = ev.get("ods:hasLocation") or {}
            geo = loc.get("ods:hasGeoreference") or {}
            row = {"specimen_id": first(s.get("id")),
                   "event_index": i,
                   "specimen_name": first(a.get("ods:specimenName")),
                   "organisation": first(a.get("ods:organisationName")),
                   "dataset": first(a.get("dwc:datasetName"))}
            row.update({f.removeprefix("dwc:"): first(loc.get(f)) for f in LOC_FIELDS})
            row.update({f.removeprefix("dwc:"): first(geo.get(f)) for f in GEO_FIELDS})
            rows.append(row)
    df = pd.DataFrame(rows, columns=LOC_COLUMNS)
    for col in ["decimalLatitude", "decimalLongitude", "coordinateUncertaintyInMeters"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


NO_LOCALITY = r"^\s*(?:no locality|unknown|s\.\s?loc)"
COORDS_IN_TEXT = r"\d+\s*[°º]|\d+\.\d+\s*[NSEW]\b"


def score_readiness(locs, max_uncertainty_m=5000):
    """How ready is each location for gazetteer matching?"""
    df = locs.copy()
    text = df["locality"].fillna("").astype(str)
    df["has_coords"] = df["decimalLatitude"].notna() & df["decimalLongitude"].notna()
    df["precise"] = df["has_coords"] & (df["coordinateUncertaintyInMeters"] <= max_uncertainty_m)
    df["has_admin"] = df[["stateProvince", "county", "municipality"]].notna().any(axis=1)
    df["no_locality"] = df["locality"].isna() | text.str.contains(NO_LOCALITY, case=False)
    df["coords_in_text"] = ~df["no_locality"] & text.str.contains(COORDS_IN_TEXT)
    df["readiness"] = np.select(           # R: case_when(), first match wins
        [df["precise"],
         df["has_coords"],
         df["coords_in_text"],
         ~df["no_locality"] & df["has_admin"],
         ~df["no_locality"]],
        ["A coords, uncertainty <= max",
         "B coords, uncertainty unknown or large",
         "C coords written in locality text",
         "C place name + admin unit",
         "D place name only"],
        default="E nothing to match",
    )
    return df


# %% 1. Survey: where is the georeferenced Sandbox data? -----------------------

print("All specimens:", ds_count())                    # ~13.2 M, Oct 2026
print("Georeferenced:", ds_count(hasLatitude="true"))

# Top-10 countries, institutions and datasets among georeferenced records
agg_geo = ds_agg(hasLatitude="true")
print(agg_geo[agg_geo["term"].isin(["country", "organisationName", "datasetName"])])

# Country strings are messy ("BE" vs "Belgium"). Check variants first:
print(ds_values("country", "Nor"))
print(ds_values("country", "New"))

# Regions with an authoritative gazetteer that has Indigenous-language names.
# Wildcard patterns are case-insensitive and catch variants.
regions = pd.DataFrame(
    [("Sapmi - Norway", "*Norway*", "Kartverket SSR: sme, smj, sma, sms"),
     ("Sapmi - Finland", "*Finland*", "NLS Finland Geographic Names: sme, smn, sms"),
     ("Sapmi - Sweden", "*Sweden*", "Lantmateriet place names (check access)"),
     ("Aotearoa NZ", "*Zealand*", "LINZ NZ Gazetteer: te reo Maori"),
     ("Australia", "*Australia*", "to check"),
     ("Canada", "*Canada*", "to check"),
     ("Greenland", "*Greenland*", "to check")],
    columns=["region", "country_pattern", "gazetteer"],
)

survey = regions.assign(
    n_total=[ds_count(country=p) for p in regions["country_pattern"]],
    n_coords=[ds_count(country=p, hasLatitude="true") for p in regions["country_pattern"]],
    n_locality=[ds_count(country=p, hasLocality="true") for p in regions["country_pattern"]],
)
survey["pct_coords"] = (100 * survey["n_coords"] / survey["n_total"]).round(1)
survey = survey.sort_values("n_coords", ascending=False)
print(survey)
survey.to_csv(OUTPUT / "sandbox-region-survey.csv", index=False)


# %% 2. Pull candidate specimens for one region ---------------------------------
# The API has no bounding-box or stateProvince filter, so narrow on the server:
# Option A: latitude window via q (Elasticsearch query_string range).
#           Tested 14 Oct 2026: Finland, 68-70.1 N -> 62,133 specimens.
# Option B: full-text q on place names (fallback if A errors or finds nothing).
# Hits come in index order, not at random.

def lat_range(lat_min, lat_max):
    return ("ods\\:hasEvents.ods\\:hasLocation.ods\\:hasGeoreference."
            f"dwc\\:decimalLatitude:[{lat_min} TO {lat_max}]")


def pull_region(country, lat_min, lat_max, q_names, n_max=1000):
    try:
        res = ds_search(country=country, q=lat_range(lat_min, lat_max), n_max=n_max)
    except requests.RequestException as e:
        print("Latitude query failed:", e)
        res = []
    if not res:
        print("Falling back to place-name search for", country)
        res = ds_search(country=country, hasLatitude="true", q=q_names, n_max=n_max)
    return res


# Northern Sapmi municipalities, majority-language names only: no Sámi names
# in the repo. The fallback misses localities written only in Sámi.
Q_SAPMI_NO = ("Kautokeino OR Karasjok OR Tana OR Nesseby OR Porsanger "
              "OR Kåfjord")
Q_SAPMI_FI = "Enontekiö OR Inari OR Utsjoki"

no_raw = pull_region("*Norway*", 68.5, 71.5, Q_SAPMI_NO)   # Troms + Finnmark
fi_raw = pull_region("*Finland*", 68.0, 70.1, Q_SAPMI_FI)  # northern Lapland

# For more geographic spread, pull smaller samples from narrower bands instead:
# fi_raw = [s for lo in np.arange(68, 70, 0.25)
#           for s in pull_region("*Finland*", lo, lo + 0.25, Q_SAPMI_FI, n_max=150)]

cand = score_readiness(flatten_locations(no_raw + fi_raw))
country_text = cand["country"].fillna("").astype(str)
cand["country_group"] = np.select(
    [country_text.str.contains(r"norway|^no$", case=False, regex=True),
     country_text.str.contains(r"finland|^fi$", case=False, regex=True)],
    ["NO", "FI"],
    default="other",
)

# Luomus (FI) records: municipality sits in dwc:county, and coordinates are
# often generalised (3-100 km uncertainty), so expect many "B" rows there.
print(count(cand, "country_group", "readiness"))
print(cand["decimalLatitude"].describe())       # sanity check of the latitude window
print(count(cand, "country_group", "dataset", sort=True).head(10))
cand.to_csv(OUTPUT / "sandbox-candidates-sapmi.csv", index=False, na_rep="NA")


# %% 3. Gazetteer hit test -------------------------------------------------------
# For a random set of georeferenced candidates, list the named places around
# the point (search radius follows the coordinate uncertainty) and measure:
#   - proximity: is there any Indigenous-language name nearby?
#   - name match: does a place name in the specimen's locality text match a
#     gazetteer place, and does that place have an Indigenous-language name?
#     (e.g. a Finnish lake name -> its Northern Sámi name). This is the
#     enrichment we want. Example names stay out of code and repo on purpose.
# Each gazetteer name is a dict with: place_id, name_id, feature_type,
# distance_m, name, language, name_status, spelling_status (R: one row of a tibble).

# The lookup and matching functions (ssr_near, mml_near, names_in_text,
# summarise_hits, ...) live in the package since step 2:
# src/geographic_locality_mas/indigenous_names.py (R twin: R/indigenous_names.R).
# Kvensk (Kven) is a national minority language, not Indigenous: kept apart there.


def lookup_names(test_set, lookup_fun, max_radius_m=5000):
    """Look up gazetteer names around each test specimen."""
    df = test_set.copy()
    df["radius_m"] = [radius_for(u, max_m=max_radius_m)
                      for u in df["coordinateUncertaintyInMeters"]]

    def safe_lookup(row):                       # R: possibly(..., otherwise = NULL)
        try:
            return lookup_fun(row.decimalLatitude, row.decimalLongitude, radius_m=row.radius_m)
        except (GazetteerError, requests.RequestException, KeyError, TypeError, ValueError) as e:
            print("Lookup failed for", row.specimen_id, "-", e)
            return None

    df["names"] = [safe_lookup(row) for row in df.itertuples()]
    return df


HIT_COLUMNS = ["lookup_ok", "n_names", "n_indigenous", "nearest_indigenous_name",
               "nearest_indigenous_place_id", "nearest_distance_m", "matched_name",
               "matched_place_id", "indigenous_parallel", "parallel_language",
               "parallel_name_status", "parallel_id", "has_parallel"]


def summarise_table(looked_up):
    """summarise_hits() for every row of a lookup_names() table.

    Adds the place IDs and name status that the repo benchmark keeps instead of
    names, and gives parallel_language as ISO 639-3 codes.
    """
    out = []
    for row in looked_up.to_dict("records"):
        hits = summarise_hits(row["names"], row["locality"])
        hits["parallel_id"] = hits["gazetteer_place_id"]
        hits["nearest_indigenous_place_id"] = (hits["indigenous"][0]["place_id"]
                                               if hits["indigenous"] else None)
        hits["matched_place_id"] = join_unique(d["place_id"] for d in hits["matched"])
        hits["parallel_language"] = join_unique(language_info(d["language"])[0]
                                                for d in hits["parallel"])
        hits["parallel_name_status"] = join_unique(d["name_status"] for d in hits["parallel"])
        out.append({**row, "names": hits["names"], **{k: hits[k] for k in HIT_COLUMNS}})
    return pd.DataFrame(out, columns=list(looked_up.columns) + HIT_COLUMNS)


def hit_rate(summ):
    n_indigenous = pd.to_numeric(summ["n_indigenous"], errors="coerce").fillna(0)
    return pd.DataFrame([{
        "specimens": len(summ),
        "lookup_ok": int(summ["lookup_ok"].sum()),
        "indigenous_nearby": int((n_indigenous > 0).sum()),
        "locality_matched": int(summ["matched_name"].notna().sum()),
        "indigenous_parallel": int(summ["has_parallel"].sum()),
        "median_dist_m": pd.to_numeric(summ["nearest_distance_m"], errors="coerce").median(),
    }])


def sample_points(cand, group, n=25, seed=42):
    pts = cand[(cand["country_group"] == group) & cand["has_coords"]]
    pts = pts.drop_duplicates("specimen_id")
    return pts.sample(n=min(n, len(pts)), random_state=seed)   # R: slice_sample()


SHOW = ["locality", "matched_name", "indigenous_parallel", "parallel_language",
        "nearest_indigenous_name", "nearest_distance_m"]

# Norway (no key needed)
summ_no = summarise_table(lookup_names(sample_points(cand, "NO"), ssr_near, max_radius_m=5000))
print(hit_rate(summ_no))
print(summ_no[SHOW])

# Finland (needs MML_API_KEY). Check the language codes on the first result.
summ_fi = None
if MML_API_KEY:
    fi_test = lookup_names(sample_points(cand, "FI"), mml_near, max_radius_m=10000)
    all_names = [d for names in fi_test["names"] if names for d in names]
    print(count(pd.DataFrame(all_names, columns=["language"]), "language"))
    summ_fi = summarise_table(fi_test)
    print(hit_rate(summ_fi))
    print(summ_fi[["county"] + SHOW])
else:
    print("No MML_API_KEY found: skipping Finland.")


# %% 4. Save the benchmark --------------------------------------------------------
# Same core fields as data/benchmark-10.json, plus the gazetteer result.
# "match"     = locality name linked to a place with an Indigenous name
# "nearby"    = only proximity hits (weaker evidence)
# "no match"  = nothing Indigenous nearby: tests the no-result annotation
#
# Re-running draws a NEW random sample. The tests and tests/fixtures/ are made
# for the sample in data/ now: after a re-run, record the fixtures again
# (scripts/make_gazetteer_fixtures.py --record) and check the tests that name
# specimen IDs.
#
# Sámi place names are Sámi knowledge, also when they come from a state gazetteer,
# and there is no agreement yet to store or publish them. So there are two files:
# - output/benchmark-indigenous-names.json: everything, with names. Stays local
#   (output/ is git-ignored).
# - data/benchmark-indigenous.json: for the repo. Gazetteer IDs, ISO 639-3 codes
#   and name status, no name strings. Look the IDs up at the gazetteer.
#   Built from a whitelist (BENCH_PUBLIC), so a new column can't leak names.

BENCH_COLUMNS = ["specimen_id", "event_index", "specimen_name", "organisation",
                 "country", "county", "locality", "latitude", "longitude",
                 "coordinate_uncertainty_m", "gazetteer", "expected", "matched_name",
                 "matched_place_id", "indigenous_parallel", "parallel_language",
                 "parallel_name_status", "gazetteer_place_id",
                 "nearest_indigenous_name", "nearest_indigenous_place_id",
                 "nearest_distance_m"]
BENCH_PUBLIC = ["specimen_id", "event_index", "specimen_name", "organisation",
                "country", "county", "locality", "latitude", "longitude",
                "coordinate_uncertainty_m", "gazetteer", "expected",
                "matched_place_id", "parallel_language", "parallel_name_status",
                "gazetteer_place_id", "nearest_indigenous_place_id",
                "nearest_distance_m"]


def to_benchmark(summ, gazetteer, n_each=5, seed=42):
    if summ is None or summ.empty:
        return pd.DataFrame(columns=BENCH_COLUMNS)
    ok = summ[summ["lookup_ok"]].copy()
    n_indigenous = pd.to_numeric(ok["n_indigenous"], errors="coerce").fillna(0)
    ok["expected"] = np.select([ok["has_parallel"], n_indigenous > 0],
                               ["match", "nearby"], default="no match")
    parts = [g.sample(n=min(n_each, len(g)), random_state=seed)
             for _, g in ok.groupby("expected")]
    picked = pd.concat(parts) if parts else ok.iloc[0:0]
    return pd.DataFrame({
        "specimen_id": picked["specimen_id"],
        "event_index": picked["event_index"],
        "specimen_name": picked["specimen_name"],
        "organisation": picked["organisation"],
        "country": picked["country"],
        "county": picked["county"],
        "locality": picked["locality"],
        "latitude": picked["decimalLatitude"],
        "longitude": picked["decimalLongitude"],
        "coordinate_uncertainty_m": picked["coordinateUncertaintyInMeters"],
        "gazetteer": gazetteer,
        "expected": picked["expected"],
        "matched_name": picked["matched_name"],
        "matched_place_id": picked["matched_place_id"],
        "indigenous_parallel": picked["indigenous_parallel"],
        "parallel_language": picked["parallel_language"],
        "parallel_name_status": picked["parallel_name_status"],
        "gazetteer_place_id": picked["parallel_id"],
        "nearest_indigenous_name": picked["nearest_indigenous_name"],
        "nearest_indigenous_place_id": picked["nearest_indigenous_place_id"],
        "nearest_distance_m": pd.to_numeric(picked["nearest_distance_m"],
                                            errors="coerce").round(),
    })


def json_value(v):
    """NaN -> null, numpy numbers -> plain numbers, whole distances -> int."""
    if isinstance(v, (list, dict)):
        return v
    if pd.isna(v):
        return None
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


parts = [to_benchmark(summ_no, "Kartverket SSR"),
         to_benchmark(summ_fi, "NLS Finland Geographic Names")]
parts = [p for p in parts if not p.empty]
benchmark = (pd.concat(parts, ignore_index=True) if parts
             else pd.DataFrame(columns=BENCH_COLUMNS))
print(count(benchmark, "gazetteer", "expected"))


def write_bench(df, path):
    """Write a data frame as a JSON array, NaN -> null. R: write_bench()."""
    records = [{k: json_value(v) for k, v in r.items()} for r in df.to_dict("records")]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("Wrote", path)


write_bench(benchmark, OUTPUT / "benchmark-indigenous-names.json")   # local only
write_bench(benchmark[BENCH_PUBLIC], DATA / "benchmark-indigenous.json")
