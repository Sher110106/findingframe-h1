# Copied from the private repository (tests/test_hidden_identity_scorer.py); only the import lines changed.
import itertools

import numpy as np
import pytest

from h1bench import scorer
from h1bench.scorer import (
    aggregate_worlds,
    oracle_ceiling,
    paired_world_bootstrap,
    score_world,
)


def rows(categories, entities=None, scorable=None):
    entities = entities or categories
    scorable = scorable or [True] * len(categories)
    return [
        {"mention_id": str(i), "category_id": c, "entity_id": e if s else None, "entity_scorable": s}
        for i, (c, e, s) in enumerate(zip(categories, entities, scorable))
    ]


def score(labels, groups):
    return score_world({str(i): cluster for i, cluster in enumerate(groups)}, labels)


def test_perfect_and_oracle_ceiling():
    labels = rows(["c", "c", "d"], ["x", "x", "y"])
    result = score(labels, ["a", "a", "b"])
    assert result["category"]["pairwise"]["f1"] == 1
    assert result["entity"]["ceaf_e"]["f1"] == 1
    ceiling = oracle_ceiling(labels)
    for view in ("category", "entity"):
        for metric in ("pairwise", "bcubed", "muc", "ceaf_e"):
            assert ceiling[view][metric]["f1"] == 1


def test_singletons_vs_merged_gold_zero_pairwise_f1_and_defined_empty_cases():
    labels = rows(["c", "c", "c"])
    result = score(labels, ["a", "b", "c"])["category"]
    assert result["pairwise"]["precision"] == 1
    assert result["pairwise"]["recall"] == 0
    assert result["pairwise"]["f1"] == 0
    assert result["split_pair_rate"] == 1
    reverse = score(rows(["a", "b", "c"]), ["z", "z", "z"])["category"]
    assert reverse["pairwise"]["precision"] == 0
    assert reverse["pairwise"]["recall"] == 1
    assert reverse["pairwise"]["f1"] == 0


def test_overmerge_and_handcomputed_unequal_partition_metrics():
    # gold sizes 3+1, prediction sizes 2+2; one true positive pair.
    labels = rows(["g", "g", "g", "h"])
    result = score(labels, ["p", "p", "q", "q"])["category"]
    assert result["pairwise"]["true_positive_pairs"] == 1
    assert result["pairwise"]["predicted_positive_pairs"] == 2
    assert result["pairwise"]["gold_positive_pairs"] == 3
    assert result["bcubed"]["precision"] == pytest.approx(0.75)
    assert result["bcubed"]["recall"] == pytest.approx(2 / 3)
    assert result["muc"]["precision"] == pytest.approx(1 / 2)
    assert result["muc"]["recall"] == pytest.approx(1 / 2)
    assert result["ceaf_e"]["precision"] == pytest.approx(11 / 15)
    assert result["ceaf_e"]["recall"] == pytest.approx(11 / 15)
    assert result["merge_pair_rate"] == pytest.approx(0.5)
    assert result["overlink_pair_rate"] == pytest.approx(1 / 3)


def test_cluster_id_permutation_invariant():
    labels = rows(["a", "a", "b", "b"])
    expected = score(labels, ["x", "x", "y", "y"])
    for perm in itertools.permutations(["u", "v"]):
        actual = score(labels, [perm[0], perm[0], perm[1], perm[1]])
        assert actual["category"] == expected["category"]


def test_unresolved_singletons_reported_and_unscorable_entities_excluded():
    labels = rows(["a", "a", "b"], ["x", "x", None], [True, True, False])
    result = score_world({"0": "q", "1": None}, labels)
    assert result["coverage"] == {"mention_count": 3, "resolved_count": 1, "unresolved_count": 2,
                                  "unresolved_rate": pytest.approx(2 / 3), "entity_scorable_count": 2}
    assert result["entity"]["pairwise"]["gold_positive_pairs"] == 1
    assert result["entity"]["pairwise"]["true_positive_pairs"] == 0


def test_invalid_universe_duplicate_labels_and_bad_entity_contract():
    labels = rows(["a"])
    with pytest.raises(ValueError, match="extraneous"):
        score_world({"stranger": "x"}, labels)
    with pytest.raises(ValueError, match="duplicate"):
        score_world({}, labels + labels)
    bad = rows(["a"], [None])
    with pytest.raises(ValueError, match="scorable entity"):
        score_world({}, bad)


def test_aggregation_is_world_clustered_and_paired_requires_same_ids():
    result = score(rows(["x"]), ["p"])
    aggregate = aggregate_worlds({"w1": result, "w2": result, "w3": result},
                                 world_metadata={"w1": {"split": "test", "scenario_family": "alias"}}, draws=20)
    assert aggregate["overall"]["category"]["pairwise"]["f1"]["mean"] == 1
    assert aggregate["by_split"]["test"]["category"]["pairwise"]["f1"]["n_worlds"] == 1
    assert "ci95" not in aggregate_worlds({"w1": result, "w2": result}, draws=20)["overall"]["category"]["pairwise"]["f1"]
    with pytest.raises(ValueError, match="identical"):
        paired_world_bootstrap({"a": 1}, {"b": 1})
    paired = paired_world_bootstrap({"a": 1, "b": 2, "c": 3}, {"a": 0, "b": 1, "c": 2}, draws=20)
    assert paired["mean_difference"] == 1
    assert paired["effect_direction"] == "positive"


def test_aggregate_bootstrap_reproduces_direct_numpy_world_resampling():
    # Distinct world-level values via singleton-vs-merged pairwise recall.
    results = {}
    for world_id, gold_groups in enumerate((["a", "b"], ["a", "a"], ["a", "a"], ["a", "b"])):
        labels = rows(gold_groups)
        result = score(labels, ["one", "one"])
        result["category"]["pairwise"]["recall"] = [0.0, 1.0, 0.5, 0.25][world_id]
        results[str(world_id)] = result
    actual = aggregate_worlds(results, seed=42, draws=31)["overall"]["category"]["pairwise"]["recall"]
    values = np.array([0.0, 1.0, 0.5, 0.25])
    rng = np.random.default_rng(42)
    counts = rng.multinomial(4, [0.25] * 4, size=31)
    boot = counts @ values / 4
    assert actual["mean"] == pytest.approx(values.mean())
    assert actual["ci95"] == pytest.approx(np.quantile(boot, [0.025, 0.975], method="linear"))


def test_family_stratified_paired_bootstrap_is_equal_family_weighted():
    left = {"a1": 0, "a2": 2, "b1": 10, "b2": 12, "b3": 14}
    right = {key: 0 for key in left}
    strata = {"a1": "A", "a2": "A", "b1": "B", "b2": "B", "b3": "B"}
    result = paired_world_bootstrap(left, right, strata=strata, seed=42, draws=40)
    assert result["mean_difference"] == pytest.approx(6.5)  # family means 1 and 12
    assert result["n_worlds"] == 5
    assert result["n_families"] == 2
    assert result["family_weights"] == {"A": 0.5, "B": 0.5}
    assert result["family_world_counts"] == {"A": 2, "B": 3}
    assert result["stratified"] is True
    assert result["ci95"][0] <= result["mean_difference"] <= result["ci95"][1]
    with pytest.raises(ValueError, match="exactly"):
        paired_world_bootstrap(left, right, strata={"a1": "A"})


def test_bootstrap_rejects_nonfinite_values_and_nonpositive_draws():
    result = score(rows(["x"]), ["p"])
    result["category"]["pairwise"]["f1"] = float("nan")
    with pytest.raises(ValueError, match="non-finite"):
        aggregate_worlds({"a": result, "b": result, "c": result})
    with pytest.raises(ValueError, match="positive"):
        aggregate_worlds({"a": score(rows(["x"]), ["p"])}, draws=0)


@pytest.mark.parametrize(
    ("gold", "pred", "expected_p", "expected_r"),
    [
        ([{"a", "b", "c"}], [{"a"}, {"b"}, {"c"}], 1 / 6, 1 / 2),
        ([{"a"}, {"b"}, {"c"}], [{"a", "b", "c"}], 1 / 2, 1 / 6),
    ],
)
def test_ceaf_e_no_scipy_rectangular_alignment_preserves_denominators(
    monkeypatch, gold, pred, expected_p, expected_r
):
    monkeypatch.setattr(scorer, "linear_sum_assignment", None)
    result = scorer._ceaf_e(gold, pred)
    assert result["precision"] == pytest.approx(expected_p)
    assert result["recall"] == pytest.approx(expected_r)
    assert result["f1"] == pytest.approx(2 * expected_p * expected_r / (expected_p + expected_r))


def test_zero_entity_scorable_worlds_excluded_from_entity_aggregate():
    zero = score_world({"0": "all-missing"}, rows(["cat"], [None], [False]))
    valid = score_world({"0": "p", "1": "p"}, rows(["cat", "cat"], ["e", "e"]))
    combined = aggregate_worlds({"zero": zero, "one": valid})
    entity_f1 = combined["overall"]["entity"]["pairwise"]["f1"]
    assert entity_f1["mean"] == 1
    assert entity_f1["n_worlds"] == 1
    assert combined["entity_aggregation"] == {
        "eligible_worlds": 1,
        "excluded_zero_scorable_worlds": 1,
    }
    # Standard all-singleton pairwise convention remains 1, but coverage makes
    # clear that this is not successful linking and cannot influence aggregate.
    unresolved = score_world({}, rows(["a", "b"]))
    assert unresolved["category"]["pairwise"]["f1"] == 1
    assert unresolved["coverage"]["resolved_count"] == 0
