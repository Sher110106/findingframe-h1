"""Data loading and scoring built on the unmodified ``h1bench.scorer``.

Scoring follows the paper's protocol: each partition (category, entity) is scored
world by world with ``score_world``, then aggregated with ``aggregate_worlds``
(seed 42, 10,000 draws by default). A model's category numbers come from its
category partition and its entity numbers from its entity partition. A baseline
supplies one assignment for both. A world without an ``ok`` record is scored as
fully unresolved (every mention a singleton), and stays in the denominator.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from h1bench import scorer
from h1bench.schema import PARTITIONS, validate_inputs, validate_label_alignment, validate_labels

SEED = 42
DRAWS = 10000

METRICS: dict[str, tuple[str, ...]] = {
    "f1": ("bcubed", "f1"),
    "precision": ("bcubed", "precision"),
    "recall": ("bcubed", "recall"),
    "split_pair_rate": ("split_pair_rate",),
    "merge_pair_rate": ("merge_pair_rate",),
    "muc_f1": ("muc", "f1"),
    "ceaf_e_f1": ("ceaf_e", "f1"),
}

DEV_DATASETS = {"v2-pilot": "dev/v2_pilot", "v1": "dev/v1"}


def data_dir() -> Path:
    env = os.environ.get("H1BENCH_DATA")
    path = Path(env) if env else Path(__file__).resolve().parent.parent / "data"
    if not path.is_dir():
        raise FileNotFoundError(
            f"data directory not found at {path}; run from a repository checkout or set H1BENCH_DATA"
        )
    return path


def _read(path: Path) -> bytes:
    return path.read_bytes()


def load_test_inputs(path: Path | None = None) -> tuple[list[dict[str, Any]], bytes]:
    """Return (worlds, raw bytes) of the v2 test inputs. The bytes feed the input checksum."""
    path = path or data_dir() / "v2" / "test_inputs.json"
    raw = _read(path)
    payload = json.loads(raw)
    validate_inputs(payload, dev=False)
    return payload["worlds"], raw


def load_labeled(directory: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    inputs = json.loads(_read(directory / "inputs.json"))
    labels = json.loads(_read(directory / "labels.json"))
    validate_inputs(inputs, dev=True)
    validate_labels(labels)
    validate_label_alignment(inputs, labels)
    return inputs["worlds"], {w["world_id"]: w["labels"] for w in labels["worlds"]}


def load_dev(dataset: str = "v2-pilot") -> dict[str, tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]]:
    names = list(DEV_DATASETS) if dataset == "all" else [dataset]
    return {name: load_labeled(data_dir() / DEV_DATASETS[name]) for name in names}


def read_records(path: Path) -> dict[str, dict[str, Any]]:
    """Latest record per world_id from a JSONL file; unparsable lines (e.g. a cut-off last line) are skipped."""
    latest: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return latest
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict) and isinstance(record.get("world_id"), str):
                latest[record["world_id"]] = record
    return latest


def baseline_records(name: str, worlds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    from h1bench.baselines import BASELINES

    fn = BASELINES[name]
    records = {}
    for world in worlds:
        assignment = fn(world)
        records[world["world_id"]] = {
            "world_id": world["world_id"], "status": "ok", "model": name,
            "assignments": {"category": dict(assignment), "entity": dict(assignment)},
        }
    return records


def _predicted(record: dict[str, Any] | None, partition: str, mention_ids: list[str]) -> dict[str, str | None]:
    if record is None or record.get("status") != "ok":
        return {m: None for m in mention_ids}
    assignment = (record.get("assignments") or {}).get(partition) or {}
    return {m: assignment.get(m) for m in mention_ids}


def _compact_scope(cat: dict[str, Any], ent: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"n_worlds": cat["category"]["bcubed"]["f1"]["n_worlds"]}
    for part, scope in (("category", cat), ("entity", ent)):
        # A family with no entity-scorable world (v1 set_level_innumerable) has no entity metrics.
        if part not in scope:
            for name in METRICS:
                out[f"{part}_{name}"] = None
            out[f"{part}_n_worlds"] = 0
            continue
        for name, path in METRICS.items():
            node = scope[part]
            for p in path:
                node = node[p]
            out[f"{part}_{name}"] = {k: node[k] for k in ("mean", "ci95") if k in node}
        out[f"{part}_n_worlds"] = scope[part]["bcubed"]["f1"]["n_worlds"]
    unresolved = cat["coverage"]["unresolved_rate"]
    out["unresolved_mention_rate"] = {k: unresolved[k] for k in ("mean", "ci95") if k in unresolved}
    return out


def score_records(records: dict[str, dict[str, Any]], worlds: list[dict[str, Any]],
                  labels_by_world: dict[str, list[dict[str, Any]]], *, family_of: dict[str, str] | None = None,
                  draws: int = DRAWS, seed: int = SEED) -> dict[str, Any]:
    """Score prediction records against labels. Returns overall and per-family compact aggregates."""
    metadata = {w["world_id"]: {"scenario_family": (family_of or {}).get(w["world_id"], w.get("scenario_family"))}
                for w in worlds}
    metadata = {k: v for k, v in metadata.items() if v["scenario_family"] is not None}
    aggregates = {}
    for partition in PARTITIONS:
        per_world = {}
        for world in worlds:
            wid = world["world_id"]
            labels = labels_by_world[wid]
            predicted = _predicted(records.get(wid), partition, [row["mention_id"] for row in labels])
            per_world[wid] = scorer.score_world(predicted, labels)
        aggregates[partition] = scorer.aggregate_worlds(per_world, world_metadata=metadata, seed=seed, draws=draws)
    cat, ent = aggregates["category"], aggregates["entity"]
    result = {
        "overall": _compact_scope(cat["overall"], ent["overall"]),
        "by_scenario_family": {
            fam: _compact_scope(cat["by_scenario_family"][fam], ent["by_scenario_family"][fam])
            for fam in sorted(cat["by_scenario_family"])
        },
        "worlds_total": len(worlds),
        "worlds_answered": sum(1 for w in worlds if (records.get(w["world_id"]) or {}).get("status") == "ok"),
        "seed": seed, "draws": draws,
    }
    return result


def fmt_ci(node: dict[str, Any] | None) -> str:
    if node is None:
        return "n/a"
    if "ci95" in node:
        return f"{node['mean']:.3f} [{node['ci95'][0]:.3f}, {node['ci95'][1]:.3f}]"
    return f"{node['mean']:.3f}"


def fmt_mean(node: dict[str, Any] | None) -> str:
    return "n/a" if node is None else f"{node['mean']:.3f}"


def markdown_table(scores: dict[str, Any], *, title: str) -> str:
    """Overall and per-family table; category and entity F1 are shown side by side, never combined."""
    head = ("| scope | worlds | Category F1 [95% CI] | Entity F1 [95% CI] | cat split | cat merge | ent split | "
            "ent merge | unresolved |\n|---|---|---|---|---|---|---|---|---|")
    rows = []
    scopes = [("ALL", scores["overall"])] + list(scores["by_scenario_family"].items())
    for name, s in scopes:
        rows.append(
            f"| {name} | {s['n_worlds']} | {fmt_ci(s['category_f1'])} | {fmt_ci(s['entity_f1'])} | "
            f"{fmt_mean(s['category_split_pair_rate'])} | {fmt_mean(s['category_merge_pair_rate'])} | "
            f"{fmt_mean(s['entity_split_pair_rate'])} | {fmt_mean(s['entity_merge_pair_rate'])} | "
            f"{fmt_mean(s['unresolved_mention_rate'])} |")
    return f"### {title}\n\n{head}\n" + "\n".join(rows) + "\n"
