"""Map value-service results to openDS annotations (DiSSCo MAS side).

Reference implementation of the community-context annotation, with tests
(tests/test_annotations.py). The MAS in DiSSCo/demo-enrichment-service-image
builds the same annotation with shared.py (map_to_annotation_str_val,
build_class_selector, get_agent). Concept: docs/indigenous-community-context.md.

  community context of a location
      -> one oa:commenting on $['ods:hasEvents'][i]['ods:hasLocation'];
         oa:value = the comment lines (one string per line): may a Sámi community
         be connected to this locality, whom the holding institution should contact
         for collaboration and approval; ends with "Built without Sámi input." and
         the review status. Never a name.
  status error (name register lookup failed and no listed area matched)
      -> CommunityContextError: the MAS sends a failure message (job FAILED,
         can be re-run)
  no location in the specimen
      -> one oa:commenting on $['ods:hasEvents']

oa:commenting is never merged into the record and its creator can delete it.
"""

import os
from datetime import datetime, timezone

from .community_context import REVIEW_STATUS

REVIEW_NOTE = f"Review status: {REVIEW_STATUS}."
BUILT_WITHOUT = "Built without Sámi input."
EVENTS_PATH = "$['ods:hasEvents']"


class CommunityContextError(RuntimeError):
    """The community context could not be assessed (register lookup failed)."""


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


def annotation(agent, timestamp, motivation, values, selector, target, references):
    """One annotation, the same fields as shared.map_to_annotation_str_val()
    (oa:value holds one string per line)."""
    return {
        "@type": "ods:Annotation",
        "oa:motivation": motivation,
        "dcterms:creator": agent,
        "dcterms:created": timestamp,
        "oa:hasTarget": {"dcterms:identifier": target["id"], "@id": target["id"],
                         "ods:fdoType": target["type"], "@type": target["type"],
                         "oa:hasSelector": selector},
        "oa:hasBody": {"@type": "oa:TextualBody", "oa:value": list(values),
                       "dcterms:references": references or ""},
    }


def annotations_for_result(result, target, agent, timestamp):
    """The community comment for one location result of POST /v1/enrich."""
    cc = result["community_context"]
    if cc["status"] == "error":
        raise CommunityContextError(cc["message"])
    references = next((a["source_url"] for a in cc["areas"] if a.get("source_url")), "")
    return [annotation(agent, timestamp, "oa:commenting", cc["comment"],
                       class_selector(location_path(result["event_index"])), target,
                       references)]


def to_annotations(specimen, response, agent=None, timestamp=None):
    """All community-context annotations for one specimen.

    specimen: the Digital Specimen from the RabbitMQ message (message["object"]).
    response: the JSON body of POST /v1/enrich for that specimen.
    Raises CommunityContextError if a lookup failed: send a failure message.
    """
    agent = agent or mas_agent()
    timestamp = timestamp or timestamp_now()
    target = target_of(specimen)
    results = response.get("results") or []
    if not results:
        return [annotation(agent, timestamp, "oa:commenting",
                           ["No location in the specimen record: community context not "
                            "assessed.", BUILT_WITHOUT, REVIEW_NOTE],
                           class_selector(EVENTS_PATH), target, "")]
    return [a for r in results for a in annotations_for_result(r, target, agent, timestamp)]
