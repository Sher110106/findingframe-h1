import json
from pathlib import Path

import pytest

from h1bench import cli, evaluate as ev, llm
from h1bench.baselines import BASELINES

ROOT = Path(__file__).resolve().parent.parent


def run(argv):
    return cli.main(argv)


def test_smoke_passes(capsys):
    assert run(["smoke"]) == 0
    out = capsys.readouterr().out
    assert "smoke: PASS" in out and "one_group_per_world" in out


def test_score_refuses_test_split(tmp_path, capsys):
    p = tmp_path / "p.jsonl"
    p.write_text("{}\n")
    assert run(["score", "--split", "test", str(p)]) == 2
    assert "not shipped" in capsys.readouterr().err


def test_baselines_dev_scores_and_v1_warning(capsys):
    assert run(["baselines", "--split", "dev", "--dataset", "all", "--draws", "50"]) == 0
    out = capsys.readouterr().out
    assert "v1 development data has a known flaw" in out
    assert "| one_group_per_world | 0.678" in out  # v2 pilot, deterministic


def test_baselines_test_writes_predictions_then_submission(tmp_path, capsys):
    assert run(["baselines", "--split", "test", "--out-dir", str(tmp_path)]) == 0
    pred = tmp_path / "predictions_one_group_per_world.jsonl"
    assert len(pred.read_text().splitlines()) == 400
    sub = tmp_path / "submission.json"
    assert run(["make-submission", str(pred), "--model", "x", "--out", str(sub), "--date", "2026-10-02"]) == 0
    data = json.loads(sub.read_text())
    assert data["n_answered"] == 400 and data["model"] == "x" and len(data["input_sha256"]) == 64
    assert set(data["predictions"]) == {w["world_id"] for w in ev.load_test_inputs()[0]}


def test_make_submission_rejects_missing_and_unknown(tmp_path, capsys):
    worlds, _ = ev.load_test_inputs()
    recs = ev.baseline_records("one_group_per_world", worlds[:10])
    p = tmp_path / "p.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs.values()))
    assert run(["make-submission", str(p), "--model", "x", "--out", str(tmp_path / "s.json")]) == 2
    assert "have no record" in capsys.readouterr().err
    assert run(["make-submission", str(p), "--model", "x", "--out", str(tmp_path / "s.json"), "--allow-missing"]) == 0
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"world_id": "w_nope", "status": "ok", "assignments": {}}) + "\n")
    assert run(["make-submission", str(bad), "--model", "x", "--out", str(tmp_path / "s2.json"),
                "--allow-missing"]) == 2


def test_make_submission_rejects_partial_mention_cover(tmp_path, capsys):
    worlds, _ = ev.load_test_inputs()
    recs = ev.baseline_records("one_group_per_world", worlds)
    first = worlds[0]["world_id"]
    victim = next(iter(recs[first]["assignments"]["category"]))
    del recs[first]["assignments"]["category"][victim]
    p = tmp_path / "p.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs.values()))
    assert run(["make-submission", str(p), "--model", "x", "--out", str(tmp_path / "s.json")]) == 2
    assert "cover exactly" in capsys.readouterr().err


def test_score_dev_predictions_roundtrip(tmp_path, capsys):
    worlds, labels = ev.load_dev("v2-pilot")["v2-pilot"]
    recs = ev.baseline_records("raw_surface_equality", worlds)
    p = tmp_path / "p.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs.values()))
    assert run(["score", "--split", "dev", "--dataset", "v2-pilot", "--draws", "50", str(p)]) == 0
    assert "| ALL | 24 |" in capsys.readouterr().out


def test_make_submission_exit_code_nonzero_as_process(tmp_path):
    """The `h1bench` entry point must exit non-zero when it rejects a submission."""
    import subprocess
    import sys

    worlds, _ = ev.load_test_inputs()
    recs = ev.baseline_records("one_group_per_world", worlds[:3])
    p = tmp_path / "p.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs.values()))
    out = tmp_path / "s.json"
    proc = subprocess.run([sys.executable, "-m", "h1bench.cli", "make-submission", str(p), "--model", "x",
                           "--out", str(out)], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "submission rejected" in proc.stderr
    assert not out.exists()
