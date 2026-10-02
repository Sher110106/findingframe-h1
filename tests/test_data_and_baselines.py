import hashlib
import json
from pathlib import Path

import pytest

from h1bench import baselines, evaluate as ev, schema

ROOT = Path(__file__).resolve().parent.parent
LABEL_KEYS = {"category_id", "entity_id", "entity_scorable", "labels", "scenario_family", "split", "probe"}


def walk_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_keys(v)


def test_test_inputs_hold_inputs_only():
    worlds, raw = ev.load_test_inputs()
    assert len(worlds) == 400
    keys = set(walk_keys(json.loads(raw)))
    assert not keys & LABEL_KEYS
    assert all(set(w) == {"world_id", "mentions"} for w in worlds)


def test_test_inputs_not_in_family_blocks():
    worlds, _ = ev.load_test_inputs()
    ids = [w["world_id"] for w in worlds]
    assert ids == sorted(ids)


def test_no_test_labels_shipped():
    names = {p.name for p in ROOT.rglob("*.json") if ".git" not in p.parts}
    assert "labels.json" in names  # development labels only
    assert not list((ROOT / "data" / "v2").glob("*label*"))
    dev_ids = set()
    for sub in ("v2_pilot", "v1"):
        dev_ids |= {w["world_id"] for w in json.loads((ROOT / "data/dev" / sub / "labels.json").read_text())["worlds"]}
    test_ids = {w["world_id"] for w in ev.load_test_inputs()[0]}
    assert not dev_ids & test_ids


def test_dev_data_validates_and_sizes():
    dev = ev.load_dev("all")
    assert len(dev["v2-pilot"][0]) == 24 and len(dev["v1"][0]) == 900
    assert all(w["split"] in {"train", "dev"} for w in dev["v1"][0])


@pytest.mark.parametrize("name", list(baselines.BASELINES))
def test_baseline_covers_every_mention(name):
    worlds, _ = ev.load_dev("v2-pilot")["v2-pilot"]
    for w in worlds:
        out = baselines.BASELINES[name](w)
        assert set(out) == {m["mention_id"] for m in w["mentions"]}


def test_one_group_per_world_has_no_category_merge_credit_on_v2_pilot():
    worlds, labels = ev.load_dev("v2-pilot")["v2-pilot"]
    s = ev.score_records(ev.baseline_records("one_group_per_world", worlds), worlds, labels, draws=50)
    assert s["overall"]["category_f1"]["mean"] < 0.8 and s["overall"]["category_split_pair_rate"]["mean"] == 0.0


def test_baselines_import_no_findingframe_code():
    src = (ROOT / "h1bench" / "baselines.py").read_text()
    assert "fact_graph" not in src and "extraction" not in src.replace("extraction of", "")


def test_schema_rejects_extra_world_field():
    worlds, _ = ev.load_test_inputs()
    bad = {"schema_version": "1.0", "worlds": [dict(worlds[0], scenario_family="x")]}
    with pytest.raises(ValueError):
        schema.validate_inputs(bad, dev=False)


def test_unresolved_worlds_stay_in_denominator():
    worlds, labels = ev.load_dev("v2-pilot")["v2-pilot"]
    recs = ev.baseline_records("one_group_per_world", worlds)
    recs.pop(worlds[0]["world_id"])
    s = ev.score_records(recs, worlds, labels, draws=50)
    assert s["worlds_total"] == 24 and s["worlds_answered"] == 23 and s["overall"]["n_worlds"] == 24
