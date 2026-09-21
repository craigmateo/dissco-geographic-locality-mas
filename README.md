# DiSSCo Geographic Locality MAS

Prototype Machine Annotation Service (MAS) for linking biodiversity specimen locality data with Indigenous place names and cultural geographies.

This project was initiated for the **DiSSCo MAS Hackathon 2026** and explores a prototype Machine Annotation Service for linking biodiversity specimen locality data with Indigenous place names and cultural geographies.

## Overview

Natural history collections often contain geographic information recorded using historical, colonial, administrative, or otherwise externally imposed place names. These locality descriptions may not reflect Indigenous names, languages, territorial relationships, or cultural understandings of place.

This project explores how a DiSSCo Machine Annotation Service could identify geographic localities in specimen records and link them to Indigenous place names and related geographic knowledge.

Rather than replacing existing locality information, the service is intended to add contextual information through annotations while preserving the original specimen record.

## Hackathon context

This project was initiated for the DiSSCo MAS Hackathon 2026.

The hackathon project focuses on developing and testing a prototype Machine Annotation Service using specimen data available through the DiSSCo sandbox.

## Initial research question

How can biodiversity specimen locality records be computationally linked to Indigenous place names while preserving provenance, uncertainty, and the original recorded locality?

## Possible workflow

The prototype may:

1. Extract locality information from a DiSSCo Digital Specimen.
2. Identify candidate geographic entities from structured and verbatim locality fields.
3. Query one or more external geographic or cultural gazetteers.
4. Identify corresponding Indigenous place names where available.
5. Record information about the language, source, geographic entity, and provenance of each match.
6. Return the result as a DiSSCo annotation rather than modifying the original specimen record.

## Example

A specimen might contain:

```text
country: Canada
stateProvince: Ontario
locality: Toronto
decimalLatitude: 43.65
decimalLongitude: -79.38
```

A resulting annotation might link the locality to additional place-name information such as:

```json
{
  "recordedLocality": "Toronto",
  "candidatePlaceNames": [
    {
      "name": "...",
      "language": "...",
      "source": "...",
      "sourceIdentifier": "...",
      "confidence": 0.92
    }
  ]
}
```

The exact annotation model will be developed during the project.

## Design principles

The project will aim to:

* preserve the original locality information;
* avoid treating one geographic name as inherently more authoritative than another;
* retain provenance for all added information;
* distinguish between historical, contemporary, administrative, and Indigenous geographic names;
* represent uncertainty explicitly;
* avoid inferring Indigenous affiliations or names without an identifiable source;
* treat Indigenous geographic information as contextual knowledge rather than simply an alternative spelling of an official place name.

## Data

Candidate specimen datasets will be selected from the DiSSCo sandbox.

Useful specimen fields may include:

* `dwc:country`
* `dwc:stateProvince`
* `dwc:county`
* `dwc:municipality`
* `dwc:locality`
* `dwc:verbatimLocality`
* `dwc:decimalLatitude`
* `dwc:decimalLongitude`

The initial dataset has not yet been selected.

Additional datasets may be considered where their licensing and availability allow them to be used in the DiSSCo hackathon environment.

## External geographic sources

Potential geographic knowledge sources will be evaluated during the project.

Selection criteria include:

* coverage of Indigenous place names;
* persistent identifiers;
* provenance information;
* language information;
* geographic coordinates or geometries;
* licensing;
* API or downloadable data access.

No particular gazetteer is assumed at this stage.

## Repository structure

```text
.
├── README.md
├── docs/
│   ├── datasets.md
│   ├── gazetteers.md
│   └── project-scope.md
├── examples/
│   ├── input/
│   └── output/
├── src/
├── tests/
└── pyproject.toml
```

## Project status

Early prototype / research stage.

Current priorities are:

* select an appropriate DiSSCo specimen dataset;
* investigate available Indigenous place-name data sources;
* define the annotation output model;
* implement a minimal locality-matching workflow;
* integrate the prototype with the DiSSCo MAS infrastructure.

## Team

DiSSCo MAS Hackathon 2026 — Geographic Place Names team.

* Craig Frayne
* Lena Thöle
* Sushil Awale
* Wolfgang Bitter

## Resources

* DiSSCo Sandbox: https://sandbox.dissco.tech/
* MAS Developer Documentation: https://dissco.github.io/mas-developers-documentation/
* DiSSCo Data Models: https://terms.dissco.tech/
* DiSSCo JSON Schemas: https://schemas.dissco.tech/schemas/
* Example MAS implementation: https://github.com/DiSSCo/demo-enrichment-service-image
* Native Lands: https://native-land.ca/maps/native-land

## License

License to be determined.
