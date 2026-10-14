"""Value service: the team's enrichment logic behind HTTP (FastAPI).

  pip install -e ".[service]"
  uvicorn geographic_locality_mas.service:app --port 8000
  GET  /health
  POST /v1/enrich {"specimen": {...}}  or  {"locations": [{...}, ...]}
  GET  /docs      OpenAPI documentation of the contract

The DiSSCo MAS (RabbitMQ side) sends the Digital Specimen it receives
(message["object"]) and maps the response to openDS annotations
(annotations.py). Contract: docs/value-service-contract.md.
Every response carries review_status ("not reviewed by Sámi representatives"),
at the top and in each indigenous_names result.

Environment (secrets come from the environment only, never from files):
  MML_API_KEY            NLS Finland API key, needed for Finnish locations
  VALUE_SERVICE_API_KEY  if set, POST /v1/enrich needs 'Authorization: Bearer <key>'.
                         Set it when the service is public: it spends our NLS
                         key, and NLS asks users to keep keys protected.
"""

import os
import secrets
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .annotations import location_path
from .indigenous_names import GAZETTEERS, REVIEW_STATUS, find_indigenous_names, num1

SERVICE = "geographic-locality-value-service"
VERSION = "0.2.0"
STATUS = Literal["match", "nearby", "no_match", "no_coordinates", "not_covered", "error"]


# ---- Request ---------------------------------------------------------------------

class Location(BaseModel):
    """One specimen location (one event). The same keys as the benchmark files."""
    model_config = ConfigDict(extra="ignore")
    specimen_id: str | None = None
    event_index: int = 0
    country: str | None = None
    country_code: str | None = None
    state_province: str | None = None
    county: str | None = None
    municipality: str | None = None
    locality: str | None = None
    verbatim_locality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    coordinate_uncertainty_m: float | None = None


class EnrichRequest(BaseModel):
    """Send either a Digital Specimen or a list of locations."""
    specimen: dict[str, Any] | None = Field(
        None, description="Digital Specimen: the bare openDS object (RabbitMQ "
                          "message['object']) or the API wrapper {'id', 'attributes'}")
    locations: list[Location] | None = None
    enrichments: list[Literal["indigenous_names"]] = ["indigenous_names"]

    @model_validator(mode="after")
    def one_input(self):
        if (self.specimen is None) == (self.locations is None):
            raise ValueError("Send either 'specimen' or 'locations', not both.")
        return self


# ---- Response --------------------------------------------------------------------

class MatchedOn(BaseModel):
    field: Literal["locality", "coordinates"]
    text: str | None
    gazetteer_name: str | None
    gazetteer_language: str | None


class IndigenousName(BaseModel):
    name: str
    language: str | None = Field(description="ISO 639-3, e.g. sme, smn, sms; fkv = Kven")
    language_name: str | None
    language_category: Literal["indigenous", "national_minority", "other"]
    gazetteer_language: str | None = Field(description="Language value as in the gazetteer")
    name_status: str | None
    spelling_status: str | None
    gazetteer: str
    place_id: str | None
    place_uri: str | None
    name_id: str | None
    feature_type: str | None
    match_type: Literal["name", "proximity"]
    matched_on: MatchedOn
    distance_m: int | None
    score: float = Field(ge=0, le=1)
    attribution: str
    licence: str
    caveats: list[str]


class Query(BaseModel):
    url: str = Field(description="First gazetteer request, without the API key")
    latitude: float
    longitude: float
    radius_m: int
    coordinate_uncertainty_m: float | None


class Summary(BaseModel):
    matched_name: str | None
    indigenous_parallel: str | None
    parallel_language: str | None
    gazetteer_place_id: str | None
    nearest_indigenous_name: str | None
    nearest_distance_m: int | None
    n_names: int | None
    n_indigenous: int | None


class IndigenousNames(BaseModel):
    specimen_id: str | None
    event_index: int | None
    status: STATUS
    gazetteer: str | None
    query: Query | None
    matches: list[IndigenousName]
    minority_language_names: list[IndigenousName]
    nearby: list[IndigenousName]
    summary: Summary | None
    message: str | None
    retrieved: str
    review_status: str = Field(REVIEW_STATUS, description="Who has reviewed these names")


class LocationResult(BaseModel):
    event_index: int
    target: str = Field(description="JSON path of the location in the specimen")
    location: Location
    indigenous_names: IndigenousNames | None = None


class EnrichResponse(BaseModel):
    service: str
    version: str
    specimen_id: str | None
    created: str
    review_status: str = Field(REVIEW_STATUS, description="Who has reviewed these names")
    results: list[LocationResult]
    message: str | None = None


# ---- Specimen -> locations ---------------------------------------------------------

def locations_from_specimen(specimen):
    """specimen_id and one flat location per event that has a location.

    Accepts the bare openDS object (what RabbitMQ delivers) and the API wrapper
    {"id": ..., "attributes": {...}}. event_index is the position in
    ods:hasEvents, so it can be used in the annotation JSON path.
    """
    attrs = specimen.get("attributes") or specimen
    specimen_id = specimen.get("id") or attrs.get("@id") or attrs.get("dcterms:identifier")
    out = []
    for i, event in enumerate(attrs.get("ods:hasEvents") or []):
        loc = (event or {}).get("ods:hasLocation")
        if not loc:
            continue
        geo = loc.get("ods:hasGeoreference") or {}
        out.append({
            "specimen_id": specimen_id,
            "event_index": i,
            "country": loc.get("dwc:country"),
            "country_code": loc.get("dwc:countryCode"),
            "state_province": loc.get("dwc:stateProvince"),
            "county": loc.get("dwc:county"),
            "municipality": loc.get("dwc:municipality"),
            "locality": loc.get("dwc:locality"),
            "verbatim_locality": loc.get("dwc:verbatimLocality"),
            "latitude": num1(geo.get("dwc:decimalLatitude")),
            "longitude": num1(geo.get("dwc:decimalLongitude")),
            "coordinate_uncertainty_m": num1(geo.get("dwc:coordinateUncertaintyInMeters")),
        })
    return specimen_id, out


# ---- App ---------------------------------------------------------------------------

app = FastAPI(title="Geographic Locality value service", version=VERSION,
              description="Enrichment API for the DiSSCo Geographic Locality MAS "
                          "(Indigenous place names: Kartverket SSR, NLS Finland).")


def check_api_key(authorization: str | None = Header(None)):
    expected = os.environ.get("VALUE_SERVICE_API_KEY")
    if not expected:
        return
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Missing or wrong API key.")


@app.get("/health")
def health():
    nls = "ready" if os.environ.get("MML_API_KEY") else "MML_API_KEY not set"
    return {"status": "ok", "service": SERVICE, "version": VERSION,
            "gazetteers": {GAZETTEERS["ssr"]["label"]: "ready",
                           GAZETTEERS["nls"]["label"]: nls}}


@app.post("/v1/enrich", response_model=EnrichResponse, dependencies=[Depends(check_api_key)])
def enrich(request: EnrichRequest):
    if request.specimen is not None:
        specimen_id, locations = locations_from_specimen(request.specimen)
    else:
        locations = [loc.model_dump() for loc in request.locations]
        specimen_id = locations[0]["specimen_id"] if locations else None
    results = []
    for loc in locations:
        result = {"event_index": loc["event_index"],
                  "target": location_path(loc["event_index"]), "location": loc}
        if "indigenous_names" in request.enrichments:
            result["indigenous_names"] = {**find_indigenous_names(loc),
                                          "review_status": REVIEW_STATUS}
        results.append(result)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return {"service": SERVICE, "version": VERSION, "specimen_id": specimen_id,
            "created": created, "review_status": REVIEW_STATUS, "results": results,
            "message": None if results else "No location in the specimen record."}
