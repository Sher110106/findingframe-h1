"""Label-blind baselines that need no FindingFrame code.

``raw_surface_equality`` and its helpers are copied from the private repository
(``evaluation/hidden_identity/baselines.py``); the two trivial baselines are copied
from ``evaluation/hidden_identity/v2/runner_v2.py``. Each function takes one world
and returns a mention_id -> cluster label map. The baselines that depend on the
FindingFrame linker are published as results only (see ``results/``).
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN = re.compile(r"\s+")


def _norm(value: Any) -> str:
    return _TOKEN.sub(" ", str(value or "").strip().casefold())


def _mentions(world: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(world, dict) or not isinstance(world.get("mentions"), list):
        raise ValueError("world must contain a mentions list")
    result = world["mentions"]
    ids = [m.get("mention_id") for m in result if isinstance(m, dict)]
    if len(ids) != len(result) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("every mention must have a non-empty string mention_id")
    if len(set(ids)) != len(ids):
        raise ValueError("mention_id values must be unique within a world")
    return result


def _groups(world: dict[str, Any], key_fn) -> dict[str, str | None]:
    groups: dict[str, str] = {}
    # Stable IDs depend only on observed input and first appearance, never labels.
    output: dict[str, str | None] = {}
    for mention in _mentions(world):
        key = key_fn(mention)
        if key is None:
            output[mention["mention_id"]] = None
        else:
            if key not in groups:
                groups[key] = f"cluster_{len(groups) + 1:06d}"
            output[mention["mention_id"]] = groups[key]
    return output


def raw_surface_equality(world: dict[str, Any]) -> dict[str, str | None]:
    """Group exact case-folded, whitespace-collapsed finding_surface strings."""
    return _groups(world, lambda m: _norm(m["frame"].get("finding_surface")))


def one_group_per_world(world: dict[str, Any]) -> dict[str, str | None]:
    return {m["mention_id"]: "all" for m in world["mentions"]}


def one_group_per_mention(world: dict[str, Any]) -> dict[str, str | None]:
    return {m["mention_id"]: m["mention_id"] for m in world["mentions"]}


BASELINES = {
    "one_group_per_world": one_group_per_world,
    "one_group_per_mention": one_group_per_mention,
    "raw_surface_equality": raw_surface_equality,
}
