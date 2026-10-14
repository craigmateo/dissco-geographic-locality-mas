# Value service ↔ MAS: JSON contract (draft 0.2, to agree)

Owner of this draft: Lena (Indigenous place names). To agree with Craig, 14 Oct 2026.
Code: `src/geographic_locality_mas/service.py` (API), `annotations.py` (MAS-side mapping).
The live schema is at `/docs` and `/openapi.json` when the service runs (`uvicorn geographic_locality_mas.service:app`).

## Who does what

- **Value service** (team repo, hosted by us): takes a Digital Specimen, returns enrichment results as plain JSON. Holds the gazetteer keys.
- **MAS** (PR to DiSSCo/demo-enrichment-service-image): reads RabbitMQ, calls `POST /v1/enrich`, maps the result to openDS annotations, publishes them. No enrichment logic, no gazetteer keys.

## Endpoints

| | |
|---|---|
| `GET /health` | `{"status": "ok", "version": ..., "gazetteers": {...}}` |
| `POST /v1/enrich` | the enrichment (below) |
| Auth | `Authorization: Bearer <VALUE_SERVICE_API_KEY>` when the env var is set on the service. The MAS gets the same value as a secret. |

## Request

The MAS sends the specimen exactly as RabbitMQ delivers it (`message["object"]`, bare openDS). The API wrapper `{"id", "attributes"}` is accepted too.

```json
{"specimen": {"dcterms:identifier": "https://doi.org/SANDBOX/X16-9NF-V0S",
              "ods:fdoType": "https://doi.org/21.T11148/894b1e6cad57e921764e",
              "ods:hasEvents": [{"ods:hasLocation": {"dwc:country": "Norway",
                "dwc:locality": "Vardø by. Ved vannreservoiret",
                "ods:hasGeoreference": {"dwc:decimalLatitude": 70.3725,
                  "dwc:decimalLongitude": 31.1192,
                  "dwc:coordinateUncertaintyInMeters": 707}}}]},
 "enrichments": ["indigenous_names"]}
```

For tests and the benchmark, send flat locations instead: `{"locations": [{"locality": ..., "country": ..., "latitude": ..., "longitude": ..., "coordinate_uncertainty_m": ...}]}`. Exactly one of `specimen` or `locations`; otherwise HTTP 422.

## Response

```text
{ service, version, specimen_id, created, message,
  review_status,                              "not reviewed by Sámi representatives"
  results: [                                  one item per event that has a location
    { event_index,                            position in ods:hasEvents
      target,                                 "$['ods:hasEvents'][0]['ods:hasLocation']"
      location: {...},                        the flat location that was used
      indigenous_names: {                     one key per enrichment (room for others)
        status,                               see table below
        gazetteer, query: {url, latitude, longitude, radius_m, coordinate_uncertainty_m},
        matches: [name],                      Indigenous names of places named in the locality text
        minority_language_names: [name],      Kven: kept apart, never annotated as Indigenous
        nearby: [name],                       only when nothing matched: nearest Indigenous names
        summary: {...}, message, retrieved,
        review_status } } ] }                 the same review status
```

`results` is empty when the specimen has no location (`message` says so). `query.url` never contains an API key. `review_status` is in every response and in every annotation (prototype rule): no Sámi representative has reviewed the design or the names yet.

One **name** record:

| Field | Example | Notes |
|---|---|---|
| `name` | `Synth-0167` | spelling as in the gazetteer. Examples and tests in this repo use made-up names (`Synth-NNNN`) |
| `language`, `language_name` | `sme`, `Northern Sámi` | ISO 639-3. Kven = `fkv` |
| `language_category` | `indigenous` | or `national_minority` (Kven), `other` |
| `gazetteer_language`, `name_status`, `spelling_status` | `Nordsamisk`, `hovednavn`, `vedtatt` | raw values from the gazetteer |
| `gazetteer` | `Kartverket SSR` | or `NLS Finland Geographic Names` |
| `place_id`, `place_uri` | `263614`, `https://stadnamn.kartverket.no/fakta/263614` | NLS: `http://paikkatiedot.fi/so/1000772/<placeId>` |
| `name_id`, `feature_type` | `263614-3`, `By` | |
| `match_type` | `name` | `proximity` for `nearby` |
| `matched_on` | `{"field": "locality", "text": "Vardø", "gazetteer_name": "Vardø", "gazetteer_language": "nor"}` | `field: "coordinates"` for proximity |
| `distance_m` | `413` | from the specimen point |
| `score` | `0.9` | 0–1, goes to `ods:score` |
| `attribution`, `licence` | `© Kartverket, … CC BY 4.0` | must travel with the name |
| `caveats` | `["Official name in a state gazetteer …"]` | plain text, go to the remarks |

Score: name match 0.9, divided by the number of different Indigenous-name sets among places with the same name in the search radius; proximity 0.5 × (1 − distance / radius); historical names (SSR `historisk`) get half.

## Status → annotation (MAS)

| `status` | Meaning | Annotation |
|---|---|---|
| `match` | locality text names a gazetteer place that has an Indigenous name | `ods:adding`, one `ods:EntityRelationship` per place on `$['ods:hasEntityRelationships']` (ClassSelector), `ods:score` = best name score |
| `nearby` | only Indigenous names near the point | `oa:commenting` on `$['ods:hasEvents'][i]['ods:hasLocation']`, lists the nearest names |
| `no_match` | nothing Indigenous within the radius | `oa:commenting` on the location |
| `no_coordinates` | no decimal coordinates | `oa:commenting` on the location |
| `not_covered` | no gazetteer for the country (only NO, FI so far) | `oa:commenting` on the location (can be switched off) |
| `error` | gazetteer down, no key | MAS sends the failure message: job FAILED |
| no results | specimen without location | `oa:commenting` on `$['ods:hasEvents']` |

Entity relationship (same keys as `shared.map_to_entity_relationship()`, plus remarks):

```json
{"@type": "ods:EntityRelationship",
 "dwc:relationshipOfResource": "hasIndigenousPlaceName",
 "dwc:relatedResourceID": "https://stadnamn.kartverket.no/fakta/263614",
 "ods:relatedResourceURI": "https://stadnamn.kartverket.no/fakta/263614",
 "dwc:relationshipEstablishedDate": "2026-10-14T12:00:00.000Z",
 "dwc:relationshipRemarks": "Indigenous-language name(s) of this place: Synth-0167 (Northern Sámi, sme; name status hovednavn). Source: Kartverket SSR, place 263614. Matched on locality text 'Vardø' (gazetteer name Vardø, nor). Official name in a state gazetteer (Kartverket SSR), not community-sourced Indigenous knowledge. © Kartverket, Sentralt stedsnavnregister (SSR), CC BY 4.0. Review status: not reviewed by Sámi representatives.",
 "ods:hasAgents": ["<MAS agent>"]}
```

Places with a best score below 0.5 are not added as relationships; the comment describes them instead.

## Rules the contract carries

- State gazetteer names are official names, not community-sourced, but Sámi place names are still Sámi knowledge: source, language, status and ID always go into the remarks, and every response and annotation carries the review status.
- No Sámi or Kven names are stored in this repo: `data/benchmark-indigenous.json` keeps gazetteer IDs, and the tests, fixtures and examples use made-up names. Real recordings stay local (`output/fixtures-recorded/`, git-ignored).
- Kven (Kvensk) is a national minority language, not Indigenous: `minority_language_names` only, never an annotation.
- SSR `Adressenavn` are skipped. SSR names marked `feilført` or `avslått` are dropped; `historisk` names are flagged.
- Keys live only in the value service environment (`MML_API_KEY`). NLS changed its open API terms on 29.9.2026: users must protect their key and NLS may block misuse, so the public endpoint needs `VALUE_SERVICE_API_KEY`.

## To agree (proposal in bold)

1. Request: **MAS sends the whole specimen**; the service extracts one location per event (handles bare openDS and the API wrapper). Alternative: MAS calls `extract_localities()` itself.
2. **One `results` item per event with a location**, with `event_index` and the target JSON path. `extract_localities()` could adopt the same keys (`event_index`, `county`, `coordinate_uncertainty_m`, …) so there is one extractor.
3. **Each enrichment under its own key** in a result (`indigenous_names`, later e.g. `gazetteer_matches`, `validation`), chosen with `enrichments` in the request.
4. `dwc:relationshipOfResource` = **`hasIndigenousPlaceName`**. `dwc:relatedResourceID`: **the place URI**, or the bare ID as the GBIF linker does?
5. **One relationship per place**, all its Indigenous names in the remarks (Inari → one ER with its Inari, Northern and Skolt Sámi names). Alternative: one per name.
6. `nearby` (proximity only) → **comment, not a relationship**. Relationship threshold **0.5**.
7. `not_covered` → **comment** (every specimen gets an answer) or no annotation?
8. `error` → **job FAILED** (can be re-run) rather than a comment.
9. Selector for adding: **`$['ods:hasEntityRelationships']`** as the deployed GBIF/ENA linkers do (the template uses `[0]`).
10. Sámi names as `oa:commenting` until a DiSSCo–Sámi agreement exists, instead of `ods:adding`? Comments cannot be merged into the record. In DiSSCo's current code an `ods:adding` annotation cannot be deleted once it is approved or rejected, and only its creator (the MAS) or an admin can delete it.

## Examples

`docs/examples/enrich-request.json`, `enrich-response.json`, `annotations.json` (Vardø: Northern Sámi + Kven). Made by `python scripts/make_contract_examples.py` from the gazetteer responses recorded on 14 Oct 2026 (`tests/fixtures/`, `scripts/make_gazetteer_fixtures.py --record`), with every Sámi and Kven name replaced by a made-up name.
