"""Mocked gazetteer HTTP for tests and examples (no network, no key).

FakeGazetteers stands in for the requests session of
geographic_locality_mas.indigenous_names and answers Kartverket SSR and NLS
Finland requests from tests/fixtures/gazetteer-*.json
(see scripts/make_gazetteer_fixtures.py for how those files are made).
"""

import json
import math
from pathlib import Path
from urllib.parse import urlencode

from geographic_locality_mas import indigenous_names as ina

FIXTURES = Path(__file__).parent / "fixtures"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class FakeResponse:
    def __init__(self, url, body, status_code=200):
        self.url, self._body, self.status_code = url, body, status_code

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        if self._body is None:
            raise ValueError("no JSON")
        return self._body


class FakeGazetteers:
    """requests.Session stand-in that replays recorded or synthetic responses.

    calls: every (url, params) the module sent.
    status: set e.g. {"nls": 500} to make one gazetteer fail.
    extra: {"ssr": [entry, ...]} adds entries (same format as the files).
    """

    def __init__(self):
        self.entries = {"ssr": read_json(FIXTURES / "gazetteer-ssr.json")["entries"],
                        "nls": read_json(FIXTURES / "gazetteer-nls.json")["entries"]}
        self.calls, self.status = [], {}

    def add(self, gaz, entry):
        self.entries[gaz] = [entry] + self.entries[gaz]

    def get(self, url, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((url, params))
        full = f"{url}?{urlencode(params)}"
        gaz = "ssr" if url.startswith(ina.SSR_API) else "nls" if url.startswith(ina.MML_API) else None
        if gaz in self.status:
            return FakeResponse(full, None, self.status[gaz])
        for e in self.entries.get(gaz, []):
            if gaz == "ssr" and same_ssr_request(e["request"], params):
                page = next(p for p in e["pages"] if p["side"] == int(params["side"]))
                return FakeResponse(full, page["body"])
            if gaz == "nls" and e["request"]["bbox"] == params.get("bbox"):
                page = next(p for p in e["pages"] if p["next"] == params.get("next"))
                return FakeResponse(full, page["body"])
        raise LookupError(f"No fixture for {url} {params}")


def same_ssr_request(request, params):
    return (math.isclose(float(params["nord"]), request["nord"])
            and math.isclose(float(params["ost"]), request["ost"])
            and int(params["radius"]) == request["radius"])


def ssr_entry(lat, lon, radius, places):
    """A one-page SSR /punkt response. places: (stedsnummer, type, metres, names),
    names: (spelling, language, status)."""
    navn = [{"stedsnummer": pid, "navneobjekttype": ftype, "meterFraPunkt": dist,
             "stedstatus": "aktiv",
             "stedsnavn": [{"skrivemåte": n, "språk": lang, "navnestatus": status,
                            "skrivemåtestatus": "vedtatt", "stedsnavnnummer": i + 1}
                           for i, (n, lang, status) in enumerate(names)]}
            for pid, ftype, dist, names in places]
    body = {"metadata": {"side": 1, "treffPerSide": 500, "totaltAntallTreff": len(navn),
                         "viserFra": 1, "viserTil": len(navn)}, "navn": navn}
    return {"request": {"nord": lat, "ost": lon, "radius": radius},
            "pages": [{"side": 1, "body": body}]}
