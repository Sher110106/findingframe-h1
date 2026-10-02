"""Input, label and prediction validation for H1 worlds.

The structural checks on inputs follow the benchmark's private validator
(frame-field allowlist, non-empty text slots, integer coordinates, unique
coordinates). Checks that need generator internals (per-family structural
variety) are not included. Label validation applies only to the development
data, whose labels ship with this repository.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = "1.0"
FRAME_FIELDS = {
    "source_report_id", "source_timeline_index", "frame_index", "finding_type", "anatomy", "laterality",
    "assertion", "measurement", "temporal_change", "finding_surface", "evidence_text",
}
TEXT_FIELDS = (
    "source_report_id", "finding_type", "anatomy", "laterality", "assertion", "finding_surface", "evidence_text",
)
MENTION_REQUIRED = {"mention_id", "frame"}
MENTION_OPTIONAL = {"descriptor"}
TEST_WORLD_FIELDS = {"world_id", "mentions"}
DEV_WORLD_FIELDS = {"world_id", "scenario_family", "split", "mentions"}
MIN_MENTIONS, MAX_MENTIONS = 6, 14  # v1 worlds hold 6-8 mentions, v2 worlds 8-14
LABEL_FIELDS = {"mention_id", "category_id", "entity_id", "entity_scorable"}
STATUSES = {"ok", "failed_api", "failed_parse"}
PARTITIONS = ("category", "entity")


def _keys(value: Any, expected: set[str], name: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{name} fields must be exactly {sorted(expected)}")


def validate_inputs(data: dict[str, Any], *, dev: bool) -> None:
    """Validate an inputs file. ``dev`` data carries scenario_family and split; test data must not."""
    _keys(data, {"schema_version", "worlds"}, "inputs")
    if data["schema_version"] != SCHEMA_VERSION or not isinstance(data["worlds"], list):
        raise ValueError("invalid input schema version or worlds")
    world_fields = DEV_WORLD_FIELDS if dev else TEST_WORLD_FIELDS
    world_ids: set[str] = set()
    mention_ids: set[str] = set()
    for world in data["worlds"]:
        _keys(world, world_fields, "world")
        if not isinstance(world["world_id"], str) or not world["world_id"]:
            raise ValueError("world_id must be a nonempty string")
        if world["world_id"] in world_ids:
            raise ValueError("duplicate world_id")
        world_ids.add(world["world_id"])
        if dev and world["split"] not in {"train", "dev"}:
            raise ValueError("development worlds must have split train or dev")
        mentions = world["mentions"]
        if not isinstance(mentions, list) or not MIN_MENTIONS <= len(mentions) <= MAX_MENTIONS:
            raise ValueError(f"world must contain {MIN_MENTIONS}-{MAX_MENTIONS} mentions")
        coordinates: set[tuple[str, int, int]] = set()
        for mention in mentions:
            optional = {key for key in MENTION_OPTIONAL if key in mention} if isinstance(mention, dict) else set()
            _keys(mention, MENTION_REQUIRED | optional, "mention")
            if mention["mention_id"] in mention_ids:
                raise ValueError("duplicate mention_id")
            mention_ids.add(mention["mention_id"])
            frame = mention["frame"]
            if not isinstance(frame, dict) or set(frame) != FRAME_FIELDS:
                raise ValueError("frame fields do not match the public contract")
            if not all(isinstance(frame[f], str) and frame[f] for f in TEXT_FIELDS):
                raise ValueError("frame text fields must be nonempty strings")
            for f in ("source_timeline_index", "frame_index"):
                if not isinstance(frame[f], int) or isinstance(frame[f], bool) or frame[f] < 0:
                    raise ValueError("timeline and frame indices must be non-negative integers")
            coordinate = (frame["source_report_id"], frame["source_timeline_index"], frame["frame_index"])
            if coordinate in coordinates:
                raise ValueError("duplicate report/timeline/frame coordinate")
            coordinates.add(coordinate)


def validate_labels(data: dict[str, Any]) -> None:
    _keys(data, {"schema_version", "worlds"}, "labels")
    if data["schema_version"] != SCHEMA_VERSION or not isinstance(data["worlds"], list):
        raise ValueError("invalid labels schema version or worlds")
    world_ids: set[str] = set()
    mention_ids: set[str] = set()
    for world in data["worlds"]:
        _keys(world, {"world_id", "labels"}, "label world")
        if world["world_id"] in world_ids:
            raise ValueError("duplicate label world_id")
        world_ids.add(world["world_id"])
        for label in world["labels"]:
            _keys(label, LABEL_FIELDS, "label")
            if label["mention_id"] in mention_ids:
                raise ValueError("duplicate label mention_id")
            mention_ids.add(label["mention_id"])
            if not isinstance(label["entity_scorable"], bool):
                raise ValueError("entity_scorable must be bool")
            if not isinstance(label["category_id"], str) or not label["category_id"]:
                raise ValueError("category_id must be a nonempty string")
            if label["entity_scorable"] and (not isinstance(label["entity_id"], str) or not label["entity_id"]):
                raise ValueError("scorable entity must have a nonempty entity_id")
            if not label["entity_scorable"] and label["entity_id"] is not None:
                raise ValueError("nonscorable entity must not carry an entity_id")


def validate_label_alignment(inputs: dict[str, Any], labels: dict[str, Any]) -> None:
    input_worlds = {w["world_id"]: {m["mention_id"] for m in w["mentions"]} for w in inputs["worlds"]}
    label_worlds = {w["world_id"]: {x["mention_id"] for x in w["labels"]} for w in labels["worlds"]}
    if input_worlds != label_worlds:
        raise ValueError("input and label worlds or mentions do not align")


def validate_record(record: Any, world: dict[str, Any]) -> list[str]:
    """Return problems found in one prediction record for ``world`` (empty list = valid)."""
    problems: list[str] = []
    if not isinstance(record, dict):
        return ["record is not an object"]
    status = record.get("status")
    if status not in STATUSES:
        problems.append(f"status must be one of {sorted(STATUSES)}")
        return problems
    assignments = record.get("assignments")
    if status != "ok":
        if assignments not in (None, {}):
            problems.append("a failed record must not carry assignments")
        return problems
    if not isinstance(assignments, dict) or set(assignments) != set(PARTITIONS):
        return ["assignments must have exactly the keys category and entity"]
    expected = {m["mention_id"] for m in world["mentions"]}
    for partition in PARTITIONS:
        part = assignments[partition]
        if not isinstance(part, dict):
            problems.append(f"{partition} must map mention_id to a cluster label")
            continue
        if set(part) != expected:
            problems.append(f"{partition} must cover exactly the world's mention ids")
        if not all(v is None or isinstance(v, str) for v in part.values()):
            problems.append(f"{partition} cluster labels must be strings or null")
    return problems


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
