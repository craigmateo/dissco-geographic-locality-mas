# DiSSCo Geographic Locality MAS

A collaborative prototype Machine Annotation Service (MAS) for enriching geographic locality information in biodiversity specimen records.

Developed for the **DiSSCo MAS Hackathon 2026**.

## Overview

Natural history collections contain geographic information recorded in many forms: place names, historical names, multilingual descriptions, coordinates, and references to geographic features.

Some records contain detailed locality descriptions but lack structured coordinates or geographic identifiers. Others contain coordinates that could benefit from validation or additional geographic context.

This project explores how a DiSSCo Machine Annotation Service can enrich geographic locality information while preserving the original specimen record, documenting provenance, and representing uncertainty.

The project also provides a foundation for more specialized enrichment, including **Indigenous place names and cultural geographies**, which formed part of the original project proposal.

## Project objectives

Our shared goal is to develop a prototype service that can:

1. Extract geographic information from DiSSCo Digital Specimens.
2. Identify geographic entities mentioned in locality descriptions.
3. Link geographic entities to external gazetteers and persistent identifiers.
4. Evaluate candidate matches using available geographic context.
5. Return structured enrichment suggestions with provenance and uncertainty.
6. Integrate these results into the DiSSCo Machine Annotation Service framework.

The original specimen data should remain unchanged.

## Potential workstreams

The following are possible areas of contribution. They are not fixed assignments, and the team will determine priorities collaboratively.

### 1. Geographic locality extraction

Extract locality descriptions, countries, administrative regions, coordinates, and other geographic information from DiSSCo Digital Specimens.

Potential tasks include parsing coordinates embedded in text, recognizing geographic features, and interpreting simple spatial expressions.

### 2. Gazetteer matching and geographic identifiers

Identify geographic entities using external sources such as Wikidata, GeoNames, or other suitable gazetteers.

Explore candidate ranking, ambiguity, alternative spellings, and persistent identifiers.

### 3. Historical and multilingual place names

Investigate locality descriptions containing historical names, variant spellings, or multiple languages.

Examples include historical regional names and descriptions combining place names with directional information.

### 4. Indigenous place names and cultural geographies (optional)

Explore whether specimen locality records can be linked to Indigenous place names, languages, and geographic knowledge using appropriate, identifiable sources.

This workstream was part of the original project concept and remains an option for interested team members.

It raises additional considerations involving provenance, cultural context, source authority, data governance, and the representation of Indigenous geographic knowledge.

The aim would be to add contextual information rather than replace existing locality descriptions or assume that different geographic naming systems are interchangeable.

### 5. Geographic validation

Investigate whether existing coordinates are consistent with locality descriptions, countries, and geographic features.

Potential outputs include validation flags and uncertainty information rather than automatic corrections.

### 6. DiSSCo MAS integration

Develop the interface needed to run the enrichment workflow as a DiSSCo Machine Annotation Service and return results in an appropriate annotation format.

## Initial dataset

We explored the DiSSCo Sandbox API and retrieved an initial sample of 100 digital specimens.

In this exploratory sample:

- 69 records contained locality descriptions.
- 80 contained country information.
- 34 contained structured coordinates.
- 35 contained locality descriptions but lacked structured coordinates.

These findings are from the first 100 returned records and should not be interpreted as representative statistics for the entire DiSSCo collection.

We selected ten example records covering different geographic interpretation challenges.

The benchmark is available at `data/benchmark-10.json`.

Examples include:

- `Rijnsburg` — straightforward geographic matching.
- `Batavia` — historical or ambiguous place name.
- `Milos, sw. Zefira, 30m üdM` — multilingual spatial description.
- `70 km N of Rovaniemi` — relative geographic position.
- `Basilan Strait` — geographic feature.
- Bangladesh locality descriptions containing coordinates embedded in text.

## Getting started

Requirements: Python 3.10 or newer, Git, and Make.

Clone the repository:

```bash
git clone https://github.com/craigmateo/dissco-geographic-locality-mas.git
cd dissco-geographic-locality-mas
```

Install the development environment:

```bash
make setup
```

Run the tests:

```bash
make test
```

Run the demonstration:

```bash
make demo
```

The initial demonstration extracts geographic locality information from a sample DiSSCo specimen and outputs structured JSON.

Live gazetteer resolution and DiSSCo MAS deployment are planned development tasks, not yet implemented.


### Exploring live DiSSCo data

The repository includes a simple client for the [DiSSCo Sandbox](https://sandbox.dissco.tech/).

After completing `make setup`, run:

```bash
make fetch
```

This retrieves five digital specimens from the Sandbox search API and extracts their geographic locality information.

The command requires an internet connection but does not require an API key or DiSSCo account for the currently accessible public search endpoint.

The API endpoint is:

`https://sandbox.dissco.tech/api/digital-specimen/v1/search`

Geographic information is extracted from the nested `ods:hasEvents` → `ods:hasLocation` structure, including coordinates stored in `ods:hasGeoreference`.

The repository also contains `data/benchmark-10.json`, a small collection of real Sandbox locality examples for testing enrichment approaches.

**Current limitations:** The live-data client retrieves the first five records. Filtering, pagination, gazetteer matching, and MAS integration are future development tasks.

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── tests.yml                # GitHub Actions automated tests
├── data/
│   ├── benchmark-10.json           # Ten real DiSSCo locality examples
│   └── sample-specimen.json        # Example specimen for the demo
├── docs/                           # Architecture and project documentation
├── scripts/
│   └── fetch_specimens.py          # Retrieve specimens from the live DiSSCo API
├── src/
│   └── geographic_locality_mas/
│       ├── __init__.py
│       ├── cli.py                   # Command-line demonstration
│       └── extraction.py            # Extract locality information
├── tests/
│   └── test_extraction.py          # Automated extraction tests
├── .gitignore
├── Makefile                        # setup, test, demo, fetch
├── pyproject.toml                  # Python package and dependencies
└── README.md
```

The project currently provides locality extraction and live DiSSCo API access. Gazetteer matching, geographic validation, and MAS integration are planned components that can be developed as separate workstreams during the hackathon.

## Collaboration

This is a collaborative hackathon project. The workstreams are intended as starting points for discussion rather than predetermined assignments.

Contributors are encouraged to:

1. Discuss or create a GitHub Issue for a proposed task.
2. Create a feature branch.
3. Implement a small, testable change.
4. Open a pull request for review.

Different approaches to geographic enrichment can be developed independently and compared using the shared benchmark.

## Design principles

- Preserve original specimen information.
- Distinguish source data from inferred or enriched information.
- Record provenance and persistent identifiers wherever possible.
- Represent ambiguity and uncertainty explicitly.
- Avoid assigning precise coordinates without adequate evidence.
- Support multilingual, historical, and alternative geographic names.
- Respect the provenance, context, and governance of Indigenous geographic knowledge when relevant.
- Keep the prototype modular and reproducible.

## Team

DiSSCo MAS Hackathon 2026 — Geographic Place Names team.

- Craig Frayne
- Lena Thöle
- Sushil Awale
- Wolfgang Bitter

## Resources

- [DiSSCo Sandbox](https://sandbox.dissco.tech/)
- [MAS Developer Documentation](https://dissco.github.io/mas-developers-documentation/)
- [DiSSCo Data Models](https://terms.dissco.tech/)
- [DiSSCo JSON Schemas](https://schemas.dissco.tech/schemas/)
- [Example MAS implementation](https://github.com/DiSSCo/demo-enrichment-service-image)

## Project status

Early working prototype.

**Implemented:** Locality extraction, sample data, command-line demonstration, and initial tests.

**Next steps:** Gazetteer resolution, benchmark evaluation, annotation output, and MAS integration.

The project scope and workstream priorities will be refined collaboratively during the hackathon.

## License

To be determined by the team.
