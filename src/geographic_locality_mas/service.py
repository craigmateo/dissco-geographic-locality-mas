"""Value service: the community context behind HTTP (FastAPI).

  pip install -e ".[service]"
  uvicorn geographic_locality_mas.service:app --port 8000
  GET  /health
  POST /v1/enrich {"specimen": {...}}  or  {"locations": [{...}, ...]}
  GET  /docs      OpenAPI documentation of the contract

The DiSSCo MAS (RabbitMQ side) sends the Digital Specimen it receives
(message["object"]) and maps the response to openDS annotations
(annotations.py). Concept: docs/indigenous-community-context.md; contract:
docs/value-service-contract.md. For each location: may a Sámi community be
connected to this locality, and whom should the holding institution contact
(community_context.assess_location). No Sámi or Kven name is in any response:
the name registers are only evidence, and the names guard refuses a response
that would hold one (HTTP 500).
Every response carries review_status ("not reviewed by Sámi representatives").

Environment (secrets come from the environment only, never from files):
  MML_API_KEY            NLS Finland API key: register evidence for Finnish locations
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
from .community_context import REVIEW_STATUS, assess_location
from .indigenous_names import GAZETTEERS, num1

SERVICE = "geographic-locality-value-service"
VERSION = "0.3.0"
CONTEXT = Literal["indigenous_context", "no_known_context", "not_assessed", "not_covered",
                  "error"]


# ---- Request ---------------------------------------------------------------------

class Location(BaseModel):
    """One specimen location (one event): the keys of locations_from_specimen()."""
    model_config = ConfigDict(extra="ignore")
    specimen_id: str | None = None
    event_index: int = 0
    organisation: str | None = None
    organisation_id: str | None = None
    country: str | None = None
    country_code: str | None = None
    state_province: str | None = None
    county: str | None = None
    municipality: str | None = None
    higher_geography: str | None = None
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
    enrichments: list[Literal["community_context"]] = ["community_context"]

    @model_validator(mode="after")
    def one_input(self):
        if (self.specimen is None) == (self.locations is None):
            raise ValueError("Send either 'specimen' or 'locations', not both.")
        return self


# ---- Response --------------------------------------------------------------------

class Institution(BaseModel):
    name: str | None
    url: str | None
    role: str
    status: str


class Contact(BaseModel):
    level: Literal["national", "local"]
    contact: str
    role: str | None
    url: str | None
    status: str = Field(description="How sure: the registry is a placeholder until the "
                                    "Sámi side decides who speaks for whom")


class CommunityContext(BaseModel):
    """community_context.assess_location() for one location. Never holds a name."""
    model_config = ConfigDict(extra="allow")
    specimen_id: str | None
    event_index: int | None
    status: CONTEXT
    country: str | None
    people: str | None
    qc: dict[str, Any] = Field(description="Coordinate check status and whether the "
                                           "coordinates were used")
    areas: list[dict[str, Any]] = Field(description="Every legally defined area the "
                                                    "recorded admin units lie in")
    evidence: dict[str, Any] | None = Field(description="Name-register evidence: counts "
                                                        "and ISO 639-3 codes only")
    institution: Institution | None = Field(description="Who should make contact")
    contacts: list[Contact] = Field(description="Whom to contact, in order")
    notice: str | None
    message: str | None
    comment: list[str] = Field(description="oa:value lines of the annotation")
    review_status: str = Field(REVIEW_STATUS, description="Who has reviewed this")


class LocationResult(BaseModel):
    event_index: int
    target: str = Field(description="JSON path of the location in the specimen")
    location: Location
    community_context: CommunityContext | None = None


class EnrichResponse(BaseModel):
    service: str
    version: str
    specimen_id: str | None
    created: str
    review_status: str = Field(REVIEW_STATUS, description="Who has reviewed this")
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
            "organisation": attrs.get("ods:organisationName"),
            "organisation_id": attrs.get("ods:organisationID"),
            "country": loc.get("dwc:country"),
            "country_code": loc.get("dwc:countryCode"),
            "state_province": loc.get("dwc:stateProvince"),
            "county": loc.get("dwc:county"),
            "municipality": loc.get("dwc:municipality"),
            "higher_geography": loc.get("dwc:higherGeography"),
            "locality": loc.get("dwc:locality"),
            "verbatim_locality": loc.get("dwc:verbatimLocality"),
            "latitude": num1(geo.get("dwc:decimalLatitude")),
            "longitude": num1(geo.get("dwc:decimalLongitude")),
            "coordinate_uncertainty_m": num1(geo.get("dwc:coordinateUncertaintyInMeters")),
        })
    return specimen_id, out


# ---- App ---------------------------------------------------------------------------

app = FastAPI(title="Geographic Locality value service", version=VERSION,
              description="Enrichment API for the DiSSCo Geographic Locality MAS: "
                          "community context (Sámi) for each specimen location.")


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
        if "community_context" in request.enrichments:
            try:
                result["community_context"] = assess_location(loc)
            except ValueError as e:             # names guard: nothing is returned
                raise HTTPException(status_code=500, detail=str(e)) from None
        results.append(result)
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return {"service": SERVICE, "version": VERSION, "specimen_id": specimen_id,
            "created": created, "review_status": REVIEW_STATUS, "results": results,
            "message": None if results else "No location in the specimen record."}
