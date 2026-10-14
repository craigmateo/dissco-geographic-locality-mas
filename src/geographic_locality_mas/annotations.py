"""Map value-service results to openDS annotations (DiSSCo MAS side).

Reference implementation of the team's annotation design, with tests
(tests/test_annotations.py). The MAS in DiSSCo/demo-enrichment-service-image
can copy these functions: the dicts follow shared.py field by field
(map_to_entity_relationship, map_to_annotation_str_val, build_class_selector).

  match     -> ods:adding of one ods:EntityRelationship per gazetteer place on
               $['ods:hasEntityRelationships'] (as the GBIF and ENA linkers),
               ods:score = the best name score of that place
  nearby, no_match, no_coordinates, not_covered
            -> oa:commenting on $['ods:hasEvents'][i]['ods:hasLocation']
  no location in the specimen
            -> oa:commenting on $['ods:hasEvents']
  error     -> IndigenousNamesError: the MAS sends a failure message (job FAILED)

Kven names (minority_language_names) are never annotated as Indigenous names.
Places whose best score is below min_score are not added as relationships;
they are described in the comment instead.
Every annotation ends with the review status (REVIEW_NOTE).
"""

import json
import os
from datetime import datetime, timezone

from .indigenous_names import REVIEW_STATUS

REVIEW_NOTE = f"Review status: {REVIEW_STATUS}."
ER_PATH = "$['ods:hasEntityRelationships']"
EVENTS_PATH = "$['ods:hasEvents']"
RELATIONSHIP = "hasIndigenousPlaceName"
MIN_SCORE = 0.5
COMMENT_ON = ("nearby", "no_match", "no_coordinates", "not_covered")


class IndigenousNamesError(RuntimeError):
    """The value service could not look up a location (gazetteer down, no key)."""


def location_path(event_index):
    return f"$['ods:hasEvents'][{event_index}]['ods:hasLocation']"


def timestamp_now():
    """Same format as shared.timestamp_now(): 2026-10-14T12:00:00.000Z"""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def mas_agent(mas_id=None, mas_name=None):
    """The MAS as agent, as shared.get_agent() builds it (MAS_ID, MAS_NAME)."""
    mas_id = mas_id or os.environ.get("MAS_ID")
    handle = f"https://hdl.handle.net/{mas_id}"
    return {
        "@id": handle,
        "@type": "schema:SoftwareApplication",
        "schema:identifier": handle,
        "schema:name": mas_name or os.environ.get("MAS_NAME"),
        "ods:hasRoles": [{"@type": "schema:Role",
                          "schema:roleName": "machine-annotation-service"}],
        "ods:hasIdentifiers": [{
            "@id": handle, "@type": "ods:Identifier", "dcterms:type": "Handle",
            "dcterms:title": "Handle", "dcterms:identifier": handle,
            "ods:isPartOfLabel": False,
            "ods:gupriLevel": "GloballyUniqueStablePersistentResolvableFDOCompliant",
            "ods:identifierStatus": "Preferred"}],
    }


def target_of(specimen):
    """Annotation target (id, type) of a Digital Specimen: bare openDS or API wrapper."""
    attrs = specimen.get("attributes") or specimen
    return {"id": attrs.get("dcterms:identifier") or attrs.get("@id") or specimen.get("id"),
            "type": attrs.get("ods:fdoType")}


def class_selector(path):
    return {"@type": "ods:ClassSelector", "ods:class": path}


def annotation(agent, timestamp, motivation, value, selector, target, references, score=None):
    """One annotation, the same fields as shared.map_to_annotation_str_val()."""
    body = {"@type": "oa:TextualBody", "oa:value": [value],
            "dcterms:references": references or ""}
    if score is not None:
        body["ods:score"] = score
    return {
        "@type": "ods:Annotation",
        "oa:motivation": motivation,
        "dcterms:creator": agent,
        "dcterms:created": timestamp,
        "oa:hasTarget": {"dcterms:identifier": target["id"], "@id": target["id"],
                         "ods:fdoType": target["type"], "@type": target["type"],
                         "oa:hasSelector": selector},
        "oa:hasBody": body,
    }


def by_place(matches):
    """Matches grouped per gazetteer place, nearest place first."""
    groups = {}
    for m in matches:
        groups.setdefault((m["gazetteer"], m["place_id"]), []).append(m)
    return list(groups.values())


def name_label(m):
    status = f"; name status {m['name_status']}" if m.get("name_status") else ""
    return f"{m['name']} ({m['language_name']}, {m['language']}{status})"


def relationship_remarks(place):
    """dwc:relationshipRemarks for one place: names, source, ID, match basis, caveats."""
    first = place[0]
    on = first["matched_on"]
    caveats = list(dict.fromkeys(c for m in place for c in m["caveats"]))
    parts = [
        "Indigenous-language name(s) of this place: "
        + "; ".join(name_label(m) for m in place) + ".",
        f"Source: {first['gazetteer']}, place {first['place_id']}.",
        (f"Matched on {on['field']} text '{on['text']}' "
         f"(gazetteer name {on['gazetteer_name']}, {on['gazetteer_language']})."),
        *caveats,
        first["attribution"] + ".",
        REVIEW_NOTE,
    ]
    return " ".join(parts)


def entity_relationship(place, agent, timestamp):
    """ods:EntityRelationship for one place, as shared.map_to_entity_relationship()
    plus dwc:relationshipRemarks."""
    first = place[0]
    return {
        "@type": "ods:EntityRelationship",
        "dwc:relationshipOfResource": RELATIONSHIP,
        "dwc:relatedResourceID": first["place_uri"] or f"{first['gazetteer']}:{first['place_id']}",
        "ods:relatedResourceURI": first["place_uri"],
        "dwc:relationshipEstablishedDate": timestamp,
        "dwc:relationshipRemarks": relationship_remarks(place),
        "ods:hasAgents": [agent],
    }


def comment_text(result, low=()):
    """oa:value of the comment on one location."""
    parts = [result["message"]]
    if result["nearby"]:
        parts.append("Nearest Indigenous-language names: " + "; ".join(
            f"{name_label(m)}, {m['distance_m']} m, {m['place_uri'] or m['place_id']}"
            for m in result["nearby"]) + ".")
    for place in low:
        parts.append(f"Low-confidence match (score {max(m['score'] for m in place)}, "
                     "not added as a relationship): "
                     + "; ".join(name_label(m) for m in place)
                     + f", {place[0]['gazetteer']} place {place[0]['place_id']}.")
    used = result["nearby"] + [m for place in low for m in place]
    if used:
        parts.append(used[0]["caveats"][0])
        parts.append(used[0]["attribution"] + ".")
    parts.append(REVIEW_NOTE)
    return " ".join(parts)


def annotations_for_result(result, target, agent, timestamp, min_score=MIN_SCORE,
                           comment_on=COMMENT_ON):
    """Annotations for one location result (one event) of POST /v1/enrich."""
    ind = result["indigenous_names"]
    if ind["status"] == "error":
        raise IndigenousNamesError(ind["message"])
    ref = (ind.get("query") or {}).get("url") or ""
    out, low = [], []
    for place in by_place(ind["matches"]):
        score = max(m["score"] for m in place)
        if score < min_score:
            low.append(place)
            continue
        er = entity_relationship(place, agent, timestamp)
        out.append(annotation(agent, timestamp, "ods:adding", json.dumps(er, ensure_ascii=False),
                              class_selector(ER_PATH), target, ref, score))
    if low or (not out and ind["status"] in comment_on):
        scores = [m["score"] for m in ind["nearby"]] + [m["score"] for p in low for m in p]
        out.append(annotation(agent, timestamp, "oa:commenting", comment_text(ind, low),
                              class_selector(location_path(result["event_index"])), target,
                              ref, max(scores) if scores else None))
    return out


def to_annotations(specimen, response, agent=None, timestamp=None, min_score=MIN_SCORE,
                   comment_on=COMMENT_ON):
    """All Indigenous place-name annotations for one specimen.

    specimen: the Digital Specimen from the RabbitMQ message (message["object"]).
    response: the JSON body of POST /v1/enrich for that specimen.
    Raises IndigenousNamesError if a lookup failed: send a failure message.
    """
    agent = agent or mas_agent()
    timestamp = timestamp or timestamp_now()
    target = target_of(specimen)
    results = response.get("results") or []
    if not results:
        return [annotation(agent, timestamp, "oa:commenting",
                           "No location in the specimen record: nothing to match against "
                           "Indigenous place names. " + REVIEW_NOTE,
                           class_selector(EVENTS_PATH), target, "")]
    return [a for r in results
            for a in annotations_for_result(r, target, agent, timestamp, min_score, comment_on)]
