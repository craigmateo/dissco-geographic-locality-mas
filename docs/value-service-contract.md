# Value service ↔ MAS: JSON contract (draft 0.3)

Owner of this draft: Lena (Indigenous workstream), 15 Oct 2026. What this part is for: [indigenous-community-context.md](indigenous-community-context.md).
Code: `src/geographic_locality_mas/service.py` (API), `community_context.py` (`assess_location`), `annotations.py` (MAS-side mapping).
The live schema is at `/docs` and `/openapi.json` when the service runs (`uvicorn geographic_locality_mas.service:app`).

Changes since 0.2: the enrichment is now `community_context`. It answers: may a Sámi community be connected to this locality, and whom should the holding institution contact? `indigenous_names` is gone from the API, so no names leave the service: the name registers are only evidence (counts and language codes).

## Who does what

- **Value service** (team repo; hosting optional): takes a Digital Specimen and returns the community context per location as plain JSON. Holds the gazetteer keys.
- **MAS** (Lena's fork of DiSSCo/demo-enrichment-service-image): reads RabbitMQ, runs `assess_location()` in-process (or calls `POST /v1/enrich` if `VALUE_SERVICE_URL` is set), maps the result to openDS annotations, publishes them.

## Endpoints

| | |
|---|---|
| `GET /health` | `{"status": "ok", "version": ..., "gazetteers": {...}}` |
| `POST /v1/enrich` | the enrichment (below) |
| Auth | `Authorization: Bearer <VALUE_SERVICE_API_KEY>` when the env var is set on the service |

## Request

```json
{"specimen": {"@id": "https://doi.org/SANDBOX/X16-9NF-V0S",
              "ods:organisationName": "University of Oslo",
              "ods:hasEvents": [{"ods:hasLocation": {"dwc:country": "Norway", "dwc:county": "Vardø",
                "dwc:locality": "Vardø by. Ved vannreservoiret",
                "ods:hasGeoreference": {"dwc:decimalLatitude": 70.3725,
                  "dwc:decimalLongitude": 31.1192,
                  "dwc:coordinateUncertaintyInMeters": 707}}}]},
 "enrichments": ["community_context"]}
```

- `specimen`: as RabbitMQ delivers it (`message["object"]`, bare openDS); the API wrapper `{"id", "attributes"}` is accepted too.
- Or `locations`: flat locations (the keys of `locations_from_specimen()`, listed in the concept), for tests and benchmarks.
- Exactly one of `specimen` or `locations`, else HTTP 422.

## Response

```text
{ service, version, specimen_id, created, message,
  review_status,                         "not reviewed by Sámi representatives"
  results: [                             one item per event that has a location
    { event_index, target, location,     target: "$['ods:hasEvents'][i]['ods:hasLocation']"
      community_context: {
        status,                          indigenous_context | no_known_context |
                                         not_assessed | not_covered | error
        country, people,                 "NO" / "FI", "Sámi"
        qc: {status, coordinates_used},  coordinate check, if one ran
        areas: [...],                    every listed area the admin units lie in
        evidence: {source, status,       name-register evidence: counts and
                   radius_m, n_names,    ISO 639-3 codes, never names
                   languages},
        institution: {name, url,         who makes the contact (from the record)
                      role, status},
        contacts: [{level, contact,      whom to contact, in order (national, local);
                    role, url, status}], status says how sure
        notice, message,
        comment: [lines],                the oa:value lines of the annotation
        review_status } } ] }
```

## Status → annotation (MAS)

| `status` | Annotation |
|---|---|
| `indigenous_context`, `no_known_context`, `not_assessed`, `not_covered` | `oa:commenting` on `$['ods:hasEvents'][i]['ods:hasLocation']`, `oa:value` = `comment` (one string per line), `dcterms:references` = the first area's legal source |
| `error` (register lookup failed, no area matched) | failure message: job FAILED (can be re-run) |
| no results (no location) | `oa:commenting` on `$['ods:hasEvents']` |
| names guard (a register name in a comment) | HTTP 500 / job FAILED, nothing published |

## Rules the contract carries

- No Sámi or Kven names in the repository, the API or annotations. Tests and examples use made-up names; real recordings stay local (`output/fixtures-recorded/`, git-ignored).
- Kven is a national minority language, not Indigenous: never counted as Sámi evidence.
- Every response and annotation carries the review status and says it was built without Sámi input.
- Keys live only in the environment (`MML_API_KEY`, `VALUE_SERVICE_API_KEY`) and never appear in results or logs.

## To agree with the team (proposals)

1. **Integration:** the integrated MAS calls `assess_location(location, qc_status)` after the coordinate check. It needs the location keys listed in the concept; `extract_localities()` could adopt them.
2. **One annotation per step and location**, so the community comment can be reviewed and withdrawn on its own.
3. **Coordinates read from the locality text don't feed the community context.** Areas are matched on admin fields only, on purpose.

## Examples

`docs/examples/enrich-request.json`, `enrich-response.json`, `annotations.json` (Vardø). Made by `python scripts/make_contract_examples.py` from the gazetteer responses recorded on 14 Oct 2026 (`tests/fixtures/`, every Sámi and Kven name made up).
