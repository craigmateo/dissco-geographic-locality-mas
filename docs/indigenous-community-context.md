# Indigenous community context (Sámi): concept

Part of the Geographic Locality MAS, DiSSCo MAS Hackathon 2026 (Geographic Place Names team). Workstream lead: Lena Thöle. Status: prototype, 15 Oct 2026.

## What it is for

For each specimen location, this part of the MAS answers one question: **may a Sámi community be connected to this locality?** If so, it adds a comment to the record saying that the community needs to be contacted for collaboration and approval before any Sámi knowledge is added to the record. The comment also names who should make the contact (the holding institution) and whom to contact (the Sámi bodies).

It does **not** add Indigenous knowledge itself. It never outputs place names or territories, and it never changes the record. Sámi place names, species names, uses and stories are Sámi knowledge, even when they appear in state registers. The MAS only makes the possible connection visible and says whom to ask: engagement, not extraction.

The prototype is built without Sámi input. Every output says so and carries the review status "not reviewed by Sámi representatives".

## How it decides, per location

1. **Read the location** of each event (`ods:hasEvents[i].ods:hasLocation`): admin units, locality text, coordinates and the holding institution.
2. **Check the coordinates.**
   - If a coordinate check ran (Craig's `validate_coordinates_with_tolerance`), `inconsistent` or `invalid_coordinates` coordinates are not used.
   - `near_boundary` coordinates are used: the Vardø test specimen is 2.2 km outside the 1:10m coastline.
   - No check, or `unable_to_validate`, means "not checked": the coordinates are used.
3. **Look for evidence**, two kinds:
   - **Legally defined Sámi areas** (`data/indigenous-areas.csv`):
     - Finland's Sámi Homeland (Act on the Sámi Parliament 974/1995, s. 4).
     - Norway's administrative area for Sámi languages (Sámi Act ch. 3 and its regulation: 14 municipalities, 4 counties).
     - These are matched on the admin fields only (`dwc:municipality`, `dwc:county`, `dwc:stateProvince`, `dwc:higherGeography`), never on the free locality text.
   - **Official name registers** (Kartverket SSR for Norway; NLS Finland, which needs `MML_API_KEY`):
     - Sámi-language names at or near the point.
     - Used only with usable coordinates. Only the count and the ISO 639-3 language codes are kept; the names never leave the module.
     - Kven names are never counted as Sámi evidence.
4. **Decide the status** (table below).
5. **Write the comment:** one `oa:commenting` on `$['ods:hasEvents'][i]['ods:hasLocation']`.

| Status | Meaning | Comment says |
|---|---|---|
| `indigenous_context` | the locality lies in a listed Sámi area, or the register has Sámi-language names there | a Sámi community may be connected; the holding institution should contact the Sámi bodies for collaboration and approval; the evidence; a candidate Local Contexts BC Notice |
| `no_known_context` | no listed area, no registered Sámi-language name | "This does not mean there is no Sámi connection." |
| `not_assessed` | no usable coordinates (or the register was not checked) and no listed area | why it was not assessed |
| `not_covered` | the country has no area layer or contact registry yet (covered: Norway, Finland) | not assessed for this country |
| `error` | the register lookup failed and no area matched | nothing; the job fails and can be re-run |

## Who is contacted

- **The holding institution** (`ods:organisationName`, `ods:organisationID`) makes the contact. It holds the specimen and is responsible for the engagement.
- **The Sámi bodies**, in order, come from `data/community-contacts.csv`:

| Country | National | Local |
|---|---|---|
| Finland | Sámi Parliament, Research Ethics Council (published FPIC procedure) | the Sámi community concerned; in the Skolt Sámi area also the Skolt Sámi Village Meeting |
| Norway | Sámi Parliament of Norway (proposed by the team, not confirmed) | to be designated by the Sámi side |

The registry is a placeholder until the Sámi side decides who speaks for whom. Every row says how sure it is, and the comment repeats that.

## Example comment (Vardø test specimen)

```text
A Sámi community may be connected to this locality. Before Sámi knowledge is added to this record, the community needs to be contacted for collaboration and approval.
Official name register (Kartverket SSR): a place named in the locality text has Sámi-language names (sme; 5 within 2000 m). Names are not copied here.
Sámi communities may hold knowledge about this place and this organism (e.g. names, uses, stories) and have rights in how this record and data from it are used. Add such knowledge only with their free, prior and informed consent.
The holding institution, University of Oslo <https://ror.org/01xtthb56>, should contact, for collaboration and approval, in this order:
1. Sámi Parliament of Norway <https://sametinget.no/>: proposed first contact [proposed by the team, not confirmed by Sámi representatives].
2. Local Sámi community (to be designated by the Sámi side) [open: who speaks for whom is for the Sámi side to decide].
Local Contexts BC Notice (candidate): the holding institution can apply it through the Local Contexts Hub.
Built without Sámi input.
Review status: not reviewed by Sámi representatives.
```

## Interface for the integrated MAS (for Craig)

One call per location:

```python
from geographic_locality_mas.community_context import assess_location

cc = assess_location(location, qc_status=check["status"])   # qc_status=None if no check ran
cc["status"]    # indigenous_context | no_known_context | not_assessed | not_covered | error
cc["comment"]   # the oa:value lines of the annotation
```

**`location`** is a flat dict. These keys come from `locations_from_specimen()` in `service.py`, which reads the bare openDS object and the API wrapper; `extract_localities()` could adopt them:

| Key | openDS |
|---|---|
| `specimen_id`, `event_index` | `@id` / `dcterms:identifier`; the position in `ods:hasEvents` |
| `organisation`, `organisation_id` | `ods:organisationName`, `ods:organisationID` |
| `country`, `country_code` | `dwc:country`, `dwc:countryCode` |
| `state_province`, `county`, `municipality`, `higher_geography` | `dwc:stateProvince`, `dwc:county`, `dwc:municipality`, `dwc:higherGeography` |
| `locality` | `dwc:locality` (used for register name matches only) |
| `latitude`, `longitude`, `coordinate_uncertainty_m` | `ods:hasGeoreference` |

**Running it:**
- Dependencies: `requests`; the two CSV files (`COMMUNITY_DATA_DIR` overrides where they are read from); `MML_API_KEY` is optional (Finland).
- No shapely, no other team code.
- **Errors:** status `error` → the MAS sends a failure message (job FAILED). The names guard raises `ValueError` if a comment would hold a register name; that also fails the job.

**Annotation:**
- One `oa:commenting` per location; `oa:value` holds the comment lines; `dcterms:references` is the first area's legal source.
- Proposal for one MAS: one annotation per step, so this comment can be reviewed and withdrawn on its own.

**Guarding other steps:**
- `names_to_guard()` and `assert_no_names(lines, names_result, location, register_names)` can check other steps' annotations too.
- For example, gazetteer labels in Sápmi can be Sámi names.
- `find_indigenous_names(location, register_names=set())` collects every Sámi and Kven name the lookup returned.
- Names that the record's own text already uses don't count.

## Rules

- No Sámi or Kven names in the repository, tests, examples or annotations. Tests use made-up names (`Synth-NNNN`).
- Kven is a national minority language, not an Indigenous one: kept apart, never counted.
- Never edit `dwc:locality` or `dwc:verbatimLocality`.
- `oa:commenting` only: it is never merged into the record, and the MAS can delete it. In DiSSCo, deleted annotations stay readable as tombstones.
- Native Land Digital is on hold: no code, no data.
- Built without Sámi input; review status in every output.

## Limits and open points

- **Coverage:** Norway and Finland only. Sweden has no area layer or contact registry yet.
- **What the evidence can show:** legal areas are administrative, not community territory. Sámi communities are connected to places outside them, and not every locality inside them concerns a community. Hence "may be connected".
- **Register evidence** needs coordinates. On the 25-specimen benchmark it finds context for 20 specimens; legal areas alone find 9. The benchmark records carry only a municipality (often one outside the 14 listed) and no county, so real records with `dwc:stateProvince` would match more areas at county level. The Vardø test specimen gets context from the register only.
- **Who speaks for whom**, and whether this is wanted at all, is for the Sámi side to decide. The next step is asking, not approving.

## Files

- Team repository, branch `feature/indigenous-place-names`:
  - `src/geographic_locality_mas/community_context.py`
  - `data/indigenous-areas.csv`, `data/community-contacts.csv`
  - `service.py`, `annotations.py`
  - `tests/test_community_context.py`
  - `docs/value-service-contract.md`
- MAS: the `geographic-locality/` folder in Lena's fork of DiSSCo/demo-enrichment-service-image.
- R twins (local, Lena): `R/community_context.R`, `R/community_annotations.R`, `R/05_community_preflight.R`.

---
*Side note: the code and this document were written with help from Claude (Anthropic).*
