"""Independent scoring for sealed-label synthetic identity partitions.

The scorer consumes predictions keyed only by observable mention IDs. Labels are
passed separately and are never used to construct a prediction partition.
Missing/None predictions are unresolved: they count as singleton clusters for
clustering metrics, but unresolved mentions are reported and never removed from
the denominator. Category labels are all scored; entity labels marked
``entity_scorable=False`` are excluded from entity metrics (e.g. set-level
findings). Empty pairwise denominators use vacuous agreement (P or R = 1); F1
is the harmonic mean. This makes all-singleton vs all-singleton perfect, and
all-singleton vs a merged prediction have zero F1. Interpret scores alongside
resolved coverage: perfect singleton scores at zero coverage are not evidence
of successful linking.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
except ImportError:  # pragma: no cover
    linear_sum_assignment = None


def _prf(p: float, r: float) -> dict[str, float]:
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0}


def _partition(items: list[str], assignments: dict[str, Any]) -> list[set[str]]:
    groups: dict[Any, set[str]] = defaultdict(set)
    for item in items:
        key = assignments.get(item)
        # Unresolved is its own singleton, never a shared null cluster.
        groups[("unresolved", item) if key is None else ("cluster", key)].add(item)
    return list(groups.values())


def _pairwise(gold: list[set[str]], pred: list[set[str]]) -> dict[str, Any]:
    gm = {m: i for i, c in enumerate(gold) for m in c}
    pm = {m: i for i, c in enumerate(pred) for m in c}
    # Compute directly by cluster intersections; avoids quadratic mention enumeration.
    intersections: Counter[tuple[int, int]] = Counter()
    for m in gm.keys() & pm.keys():
        intersections[gm[m], pm[m]] += 1
    tp = sum(n * (n - 1) // 2 for n in intersections.values())
    gp = sum(len(c) * (len(c) - 1) // 2 for c in gold)
    pp = sum(len(c) * (len(c) - 1) // 2 for c in pred)
    p = tp / pp if pp else 1.0
    r = tp / gp if gp else 1.0
    return {**_prf(p, r), "true_positive_pairs": tp, "predicted_positive_pairs": pp, "gold_positive_pairs": gp}


def _bcubed(gold: list[set[str]], pred: list[set[str]]) -> dict[str, float]:
    gm = {m: c for c in gold for m in c}
    pm = {m: c for c in pred for m in c}
    if not gm:
        return _prf(1.0, 1.0)
    precisions, recalls = [], []
    for m in gm:
        overlap = len(gm[m] & pm[m])
        precisions.append(overlap / len(pm[m]))
        recalls.append(overlap / len(gm[m]))
    return _prf(sum(precisions) / len(precisions), sum(recalls) / len(recalls))


def _muc(gold: list[set[str]], pred: list[set[str]]) -> dict[str, float]:
    def link_score(side: list[set[str]], other: list[set[str]], other_map: dict[str, int]) -> float:
        numerator = denominator = 0
        for c in side:
            denominator += len(c) - 1
            parts = len({other_map.get(m, ("missing", m)) for m in c})
            numerator += len(c) - parts
        return numerator / denominator if denominator else 1.0
    pm = {m: i for i, c in enumerate(pred) for m in c}
    gm = {m: i for i, c in enumerate(gold) for m in c}
    return _prf(link_score(pred, gold, gm), link_score(gold, pred, pm))


def _ceaf_e(gold: list[set[str]], pred: list[set[str]]) -> dict[str, float]:
    if not gold and not pred:
        return _prf(1.0, 1.0)
    if not gold or not pred:
        return _prf(0.0, 0.0)
    sim = [[2 * len(g & p) / (len(g) + len(p)) for p in pred] for g in gold]
    if linear_sum_assignment is not None:
        rows, cols = linear_sum_assignment(sim, maximize=True)
        total = sum(sim[int(i)][int(j)] for i, j in zip(rows, cols))
    else:  # exact DP assignment, preserving original side denominators
        # Every gold row may remain unmatched or align with one unused predicted
        # cluster. The rectangular assignment is valid in either orientation.
        dp = {0: 0.0}
        for row in sim:
            nxt = dict(dp)
            for mask, value in dp.items():
                for j, score in enumerate(row):
                    if not mask >> j & 1:
                        key = mask | (1 << j)
                        nxt[key] = max(nxt.get(key, 0), value + score)
            dp = nxt
        total = max(dp.values())
    return _prf(total / len(pred), total / len(gold))


def _partition_metrics(items: list[str], gold_assignments: dict[str, Any], pred_assignments: dict[str, Any]) -> dict[str, Any]:
    gold = _partition(items, gold_assignments)
    pred = _partition(items, pred_assignments)
    pair = _pairwise(gold, pred)
    bc = _bcubed(gold, pred)
    muc = _muc(gold, pred)
    ceaf = _ceaf_e(gold, pred)
    gm = {m: i for i, c in enumerate(gold) for m in c}
    pm = {m: i for i, c in enumerate(pred) for m in c}
    cross = Counter((gm[m], pm[m]) for m in items)
    overlinked = pair["predicted_positive_pairs"] - pair["true_positive_pairs"]
    gold_pairs = pair["gold_positive_pairs"]
    pred_pairs = pair["predicted_positive_pairs"]
    # Split/merge rates are pair-weighted error fractions, not cluster counts.
    return {"pairwise": pair, "bcubed": bc, "muc": muc, "ceaf_e": ceaf,
            "split_pair_rate": (gold_pairs - pair["true_positive_pairs"]) / gold_pairs if gold_pairs else 0.0,
            "merge_pair_rate": overlinked / pred_pairs if pred_pairs else 0.0,
            "overlink_pair_rate": overlinked / gold_pairs if gold_pairs else 0.0}


def score_world(predicted: dict[str, str | None], labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Score one world. Requires exact ID universe; missing predictions use None.

    A missing key is equivalent to unresolved None. Extra prediction IDs,
    duplicate label IDs, absent required labels, or non-bool scorable flags fail.
    """
    ids = [row["mention_id"] for row in labels]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate label mention_id")
    extra = set(predicted) - set(ids)
    if extra:
        raise ValueError(f"extraneous prediction IDs: {sorted(extra)!r}")
    for row in labels:
        if not {"category_id", "entity_id", "entity_scorable"} <= row.keys():
            raise ValueError("label missing required category/entity fields")
        if not isinstance(row["entity_scorable"], bool):
            raise ValueError("entity_scorable must be bool")
    cat_gold = {r["mention_id"]: r["category_id"] for r in labels}
    cat_pred = {m: predicted.get(m) for m in ids}
    entity_rows = [r for r in labels if r["entity_scorable"]]
    ent_gold = {r["mention_id"]: r["entity_id"] for r in entity_rows}
    if any(v is None for v in ent_gold.values()):
        raise ValueError("scorable entity must have entity_id")
    ent_pred = {r["mention_id"]: predicted.get(r["mention_id"]) for r in entity_rows}
    unresolved = [m for m in ids if predicted.get(m) is None]
    return {"category": _partition_metrics(ids, cat_gold, cat_pred),
            "entity": _partition_metrics(list(ent_gold), ent_gold, ent_pred),
            "coverage": {"mention_count": len(ids), "resolved_count": len(ids) - len(unresolved),
                         "unresolved_count": len(unresolved), "unresolved_rate": len(unresolved) / len(ids) if ids else 0.0,
                         "entity_scorable_count": len(entity_rows)}}


def oracle_ceiling(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Validation-only scorer ceiling; never pass these assignments to a linker."""
    category = {r["mention_id"]: f"oracle:{r['category_id']}" for r in labels}
    entity = {r["mention_id"]: f"oracle:{r['entity_id']}" for r in labels if r["entity_scorable"]}
    result = score_world(category, labels)
    result["entity"] = _partition_metrics(list(entity), entity, entity)
    return result


def aggregate_worlds(world_results: dict[str, dict[str, Any]], *, world_metadata: dict[str, dict[str, str]] | None = None, seed: int = 42, draws: int = 10000) -> dict[str, Any]:
    """Equal-world means and vectorized world-cluster bootstrap CIs.

    Sampled multiplicities are shared across all numeric columns within each
    aggregation group. Batches bound memory to at most 256 x worlds x columns;
    entity metrics use only worlds with at least one scorable entity. Percentile
    intervals use NumPy's linear quantile method. With fewer than three eligible
    worlds, report points only. CI metadata includes NumPy version and method.
    """
    if not world_results:
        raise ValueError("at least one world result is required")
    if draws <= 0:
        raise ValueError("draws must be positive")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        paths: list[tuple[str, ...]] = []
        def walk(obj: Any, path: tuple[str, ...] = ()) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items(): walk(v, path + (k,))
            elif isinstance(obj, (int, float)) and not isinstance(obj, bool): paths.append(path)
        walk(rows[0])
        out: dict[str, Any] = {}
        def put(path: tuple[str, ...], val: Any) -> None:
            node = out
            for part in path[:-1]: node = node.setdefault(part, {})
            node[path[-1]] = val
        groups: dict[str, list[tuple[str, ...]]] = {"all": [], "entity": []}
        for path in paths:
            groups["entity" if path[0] == "entity" else "all"].append(path)
        rng = np.random.default_rng(seed)
        for group, group_paths in groups.items():
            if not group_paths:
                continue
            metric_rows = rows
            if group == "entity":
                metric_rows = [row for row in rows if row["coverage"]["entity_scorable_count"] > 0]
                if not metric_rows:
                    continue
            matrix = np.asarray([[float(_get(row, path)) for path in group_paths] for row in metric_rows], dtype=np.float64)
            if not np.isfinite(matrix).all():
                raise ValueError("world results contain non-finite numeric metrics")
            n_worlds = matrix.shape[0]
            means = matrix.mean(axis=0)
            ci_by_col: dict[int, list[float]] = {}
            if n_worlds >= 3:
                # Bounded-memory multinomial multiplicities; one draw matrix is
                # reused across every metric column in this group.
                boot_means = np.empty((draws, matrix.shape[1]), dtype=np.float64)
                for start in range(0, draws, 256):
                    size = min(256, draws - start)
                    multiplicities = rng.multinomial(n_worlds, [1 / n_worlds] * n_worlds, size=size)
                    boot_means[start:start + size] = multiplicities @ matrix / n_worlds
                low, high = np.quantile(boot_means, [0.025, 0.975], axis=0, method="linear")
                ci_by_col = {i: [float(low[i]), float(high[i])] for i in range(matrix.shape[1])}
            for i, path in enumerate(group_paths):
                result: dict[str, Any] = {"mean": float(means[i]), "n_worlds": n_worlds}
                if i in ci_by_col:
                    result["ci95"] = ci_by_col[i]
                put(path, result)
        return out
    grouped: dict[str, dict[str, dict[str, Any]]] = {"scenario_family": defaultdict(dict), "split": defaultdict(dict)}
    for world_id, result in world_results.items():
        for key in grouped:
            value = (world_metadata or {}).get(world_id, {}).get(key)
            if value is not None: grouped[key][value][world_id] = result
    def entity_counts(results: dict[str, dict[str, Any]]) -> dict[str, int]:
        eligible = sum(r["coverage"]["entity_scorable_count"] > 0 for r in results.values())
        return {"eligible_worlds": eligible, "excluded_zero_scorable_worlds": len(results) - eligible}
    return {"overall": summarize(list(world_results.values())), "by_world": dict(world_results),
            "entity_aggregation": entity_counts(world_results),
            "by_scenario_family": {k: summarize(list(v.values())) for k, v in grouped["scenario_family"].items()},
            "by_split": {k: summarize(list(v.values())) for k, v in grouped["split"].items()},
            "bootstrap": {"method": "world-cluster multinomial bootstrap; batches<=256; linear percentile CI",
                          "quantile_method": "linear", "numpy_version": np.__version__},
            "seed": seed, "draws": draws}


def _get(obj: dict[str, Any], path: Iterable[str]) -> Any:
    for key in path: obj = obj[key]
    return obj


def paired_world_bootstrap(left: dict[str, float], right: dict[str, float], *, strata: dict[str, str] | None = None,
                           seed: int = 42, draws: int = 10000) -> dict[str, Any]:
    """Bootstrap paired differences, optionally equal-weighted by stratum.

    With ``strata``, resample worlds with replacement within each family, then
    compute each draw's equal-family mean (not a pooled-world mean). Both input
    score maps and the stratum map must contain identical IDs. Direction is
    reported as positive/negative/tie for ``left - right``. Percentile bounds
    use NumPy's linear quantile convention; fewer than three worlds yields a
    point estimate only.
    """
    if set(left) != set(right):
        raise ValueError("paired comparison requires identical world IDs")
    if not left:
        raise ValueError("at least one paired world is required")
    if draws <= 0:
        raise ValueError("draws must be positive")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    ids = set(left)
    if strata is not None and set(strata) != ids:
        raise ValueError("strata must contain exactly the paired world IDs")
    diffs = {key: float(left[key]) - float(right[key]) for key in ids}
    if not np.isfinite(list(diffs.values())).all():
        raise ValueError("paired scores must be finite")
    family_ids: dict[str, list[str]] = defaultdict(list)
    if strata is None:
        family_ids["__all__"] = sorted(ids)
    else:
        for world_id in sorted(ids):
            family_ids[strata[world_id]].append(world_id)
    families = sorted(family_ids)
    family_means = {family: float(np.mean([diffs[w] for w in family_ids[family]])) for family in families}
    point = float(np.mean(list(family_means.values())))
    result: dict[str, Any] = {
        "mean_difference": point,
        "effect_direction": "positive" if point > 0 else "negative" if point < 0 else "tie",
        "n_worlds": len(ids), "n_families": len(families),
        "family_weights": {family: 1 / len(families) for family in families},
        "family_world_counts": {family: len(family_ids[family]) for family in families},
        "stratified": strata is not None, "seed": seed, "draws": draws,
        "bootstrap": {"method": "paired world-cluster bootstrap; within-stratum resampling; equal-family mean",
                      "quantile_method": "linear", "numpy_version": np.__version__},
    }
    if len(ids) >= 3:
        rng = np.random.default_rng(seed)
        boot = np.zeros(draws, dtype=np.float64)
        for family in families:
            vals = np.asarray([diffs[w] for w in family_ids[family]], dtype=np.float64)
            n = len(vals)
            family_draws = np.empty(draws, dtype=np.float64)
            for start in range(0, draws, 256):
                size = min(256, draws - start)
                counts = rng.multinomial(n, [1 / n] * n, size=size)
                family_draws[start:start + size] = counts @ vals / n
            boot += family_draws / len(families)
        result["ci95"] = [float(x) for x in np.quantile(boot, [0.025, 0.975], method="linear")]
    return result
