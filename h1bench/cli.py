"""Command line interface: smoke, baselines, run, score, make-submission."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from h1bench import __version__
from h1bench import evaluate as ev
from h1bench import llm
from h1bench.baselines import BASELINES
from h1bench.schema import sha256_bytes, validate_record

V1_WARNING = (
    "NOTE: v1 development data has a known flaw. Seven of its nine families hold exactly one gold category per "
    "world (only laterality_change and report_order_permutations hold two), and every v1 test world held one, so "
    "one_group_per_world scores Category F1 = 1.000 in those families. Read v1 category numbers as over-splitting "
    "only; v2 fixes this."
)


def _summary_row(name: str, s: dict[str, Any]) -> str:
    o = s["overall"]
    return (f"| {name} | {ev.fmt_ci(o['category_f1'])} | {ev.fmt_ci(o['entity_f1'])} | "
            f"{ev.fmt_mean(o['category_split_pair_rate'])} | {ev.fmt_mean(o['category_merge_pair_rate'])} | "
            f"{ev.fmt_mean(o['entity_split_pair_rate'])} | {ev.fmt_mean(o['entity_merge_pair_rate'])} | "
            f"{ev.fmt_mean(o['unresolved_mention_rate'])} |")


SUMMARY_HEAD = ("| system | Category F1 [95% CI] | Entity F1 [95% CI] | cat split | cat merge | ent split | "
                "ent merge | unresolved |\n|---|---|---|---|---|---|---|---|")


# ---------------------------------------------------------------- smoke

def _oracle_records(worlds: list[dict[str, Any]], labels: dict[str, list[dict[str, Any]]]) -> dict[str, dict]:
    records = {}
    for w in worlds:
        rows = labels[w["world_id"]]
        records[w["world_id"]] = {
            "world_id": w["world_id"], "status": "ok",
            "assignments": {"category": {r["mention_id"]: r["category_id"] for r in rows},
                            "entity": {r["mention_id"]: r["entity_id"] for r in rows}},
        }
    return records


def _fake_chat_factory(worlds: list[dict[str, Any]], labels: dict[str, list[dict[str, Any]]]):
    """Offline stand-in for a model: first reply per world is invalid, the repair reply is the oracle answer."""
    by_prompt = {}
    for w in worlds:
        llm_mentions, m_to_real = llm.relabel_world(w)
        real_to_m = {v: k for k, v in m_to_real.items()}
        rows = labels[w["world_id"]]

        def groups(key):
            g: dict[Any, list[str]] = {}
            for r in rows:
                if r[key] is not None:
                    g.setdefault(r[key], []).append(real_to_m[r["mention_id"]])
            singles = [[real_to_m[r["mention_id"]]] for r in rows if r[key] is None]
            return list(g.values()) + singles

        answer = json.dumps({"category_groups": groups("category_id"), "entity_groups": groups("entity_id")})
        by_prompt[llm.build_initial_messages(llm_mentions)[1]["content"]] = answer

    def chat(messages):
        answer = by_prompt[messages[1]["content"]]
        if len(messages) == 2:
            return llm.ChatReply("Sure! Here is my answer:", {"total_tokens": 1}, False)
        return llm.ChatReply("Here you go: " + answer + " Hope that helps.", {"total_tokens": 1}, False)

    return chat


def cmd_smoke(args: argparse.Namespace) -> int:
    from importlib import resources

    base = resources.files("h1bench").joinpath("smoke_data")
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("inputs.json", "labels.json"):
            (Path(tmp) / name).write_bytes(base.joinpath(name).read_bytes())
        worlds, labels = ev.load_labeled(Path(tmp))
    print(f"h1bench {__version__} smoke: {len(worlds)} bundled development worlds, no network")
    draws = 200
    ok = True
    print(SUMMARY_HEAD)
    for name in BASELINES:
        s = ev.score_records(ev.baseline_records(name, worlds), worlds, labels, draws=draws)
        print(_summary_row(name, s))
        o = s["overall"]
        if name == "one_group_per_mention":
            ok &= o["category_split_pair_rate"]["mean"] == 1.0 and o["category_merge_pair_rate"]["mean"] == 0.0
    oracle = ev.score_records(_oracle_records(worlds, labels), worlds, labels, draws=draws)
    print(_summary_row("oracle (labels as predictions)", oracle))
    ok &= oracle["overall"]["category_f1"]["mean"] == 1.0 and oracle["overall"]["entity_f1"]["mean"] == 1.0
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "pred.jsonl"
        chat = _fake_chat_factory(worlds, labels)
        counts = llm.run_worlds(chat, worlds, out, model="offline-fake", concurrency=2)
        again = llm.run_worlds(chat, worlds, out, model="offline-fake", concurrency=2)
        s = ev.score_records(ev.read_records(out), worlds, labels, draws=draws)
        print(_summary_row("offline fake model (repair path)", s))
        ok &= counts["ok"] == len(worlds) and again["skipped"] == len(worlds)
        ok &= s["overall"]["category_f1"]["mean"] == 1.0
    print("smoke: PASS" if ok else "smoke: FAIL")
    return 0 if ok else 1


# ---------------------------------------------------------------- baselines

def cmd_baselines(args: argparse.Namespace) -> int:
    if args.split == "test":
        worlds, _ = ev.load_test_inputs()
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in BASELINES:
            path = out_dir / f"predictions_{name}.jsonl"
            with open(path, "w", encoding="utf-8") as fh:
                for record in ev.baseline_records(name, worlds).values():
                    fh.write(json.dumps(record, sort_keys=True) + "\n")
            print(f"wrote {path} ({len(worlds)} worlds)")
        print("test labels are not shipped: score these through a maintainer-scored submission.")
        return 0
    collected: dict[str, Any] = {}
    for dataset, (worlds, labels) in ev.load_dev(args.dataset).items():
        print(f"\n## development data: {dataset} ({len(worlds)} worlds)")
        if dataset == "v1":
            print(V1_WARNING)
        results = {n: ev.score_records(ev.baseline_records(n, worlds), worlds, labels, draws=args.draws)
                   for n in BASELINES}
        collected[dataset] = results
        print("\n" + SUMMARY_HEAD)
        for name, s in results.items():
            print(_summary_row(name, s))
        if args.by_family:
            for name, s in results.items():
                print("\n" + ev.markdown_table(s, title=f"{name} by family"))
    if args.json:
        Path(args.json).write_text(json.dumps(collected, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


# ---------------------------------------------------------------- run

def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def cmd_run(args: argparse.Namespace) -> int:
    if args.split == "test":
        worlds, _ = ev.load_test_inputs()
    else:
        worlds = [w for _, (ws, _) in ev.load_dev(args.dataset).items() for w in ws]
    if args.limit:
        worlds = worlds[: args.limit]
    out = Path(args.out or f"predictions_{args.split}_{_safe(args.model)}.jsonl")
    chat = llm.make_openai_chat(base_url=args.base_url, model=args.model, api_key_env=args.api_key_env,
                                timeout=args.timeout, max_tokens=args.max_tokens,
                                send_response_format=not args.no_response_format)

    def progress(done: int, total: int, record: dict[str, Any]) -> None:
        print(f"[{done}/{total}] {record['world_id']} {record['status']} {record['latency_s']}s", flush=True)

    counts = llm.run_worlds(chat, worlds, out, model=args.model, concurrency=args.concurrency,
                            retry_failed=args.retry_failed, progress=progress)
    print(f"wrote {out}: {counts}")
    if args.split == "dev":
        print(f"score it with: h1bench score --split dev {out}")
    else:
        print(f"make a submission with: h1bench make-submission {out} --model {args.model}")
    return 0


# ---------------------------------------------------------------- score

def cmd_score(args: argparse.Namespace) -> int:
    if args.split == "test":
        print("error: test labels are not shipped. Submit through a pull request; see SUBMITTING.md.",
              file=sys.stderr)
        return 2
    records = ev.read_records(Path(args.predictions))
    if not records:
        print(f"error: no readable records in {args.predictions}", file=sys.stderr)
        return 2
    output: dict[str, Any] = {}
    for dataset, (worlds, labels) in ev.load_dev(args.dataset).items():
        have = sum(1 for w in worlds if w["world_id"] in records)
        if have == 0:
            print(f"\n## {dataset}: no predictions for these worlds, skipped")
            continue
        s = ev.score_records(records, worlds, labels, draws=args.draws)
        output[dataset] = s
        print(f"\n## development data: {dataset} ({have}/{len(worlds)} worlds have a record; "
              f"{s['worlds_answered']} answered)")
        if dataset == "v1":
            print(V1_WARNING)
        print(ev.markdown_table(s, title=f"{dataset}"))
    if args.json:
        Path(args.json).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


# ---------------------------------------------------------------- make-submission

def cmd_make_submission(args: argparse.Namespace) -> int:
    worlds, raw = ev.load_test_inputs()
    records = ev.read_records(Path(args.predictions))
    by_id = {w["world_id"]: w for w in worlds}
    unknown = sorted(set(records) - set(by_id))
    problems: list[str] = []
    if unknown:
        problems.append(f"{len(unknown)} record(s) for unknown world_id, e.g. {unknown[:3]}")
    missing = [w["world_id"] for w in worlds if w["world_id"] not in records]
    if missing and not args.allow_missing:
        problems.append(f"{len(missing)} of {len(worlds)} worlds have no record (use --allow-missing to score "
                        "them as unresolved)")
    for wid, record in records.items():
        if wid in by_id:
            for p in validate_record(record, by_id[wid]):
                problems.append(f"{wid}: {p}")
    if problems:
        print("submission rejected:", file=sys.stderr)
        for p in problems[:20]:
            print(f"  - {p}", file=sys.stderr)
        if len(problems) > 20:
            print(f"  ... and {len(problems) - 20} more", file=sys.stderr)
        return 2
    predictions: dict[str, Any] = {}
    matches = checked = 0
    for w in worlds:
        rec = records.get(w["world_id"])
        if rec is None or rec["status"] != "ok":
            predictions[w["world_id"]] = {"status": rec["status"] if rec else "missing",
                                           "category": None, "entity": None}
            continue
        predictions[w["world_id"]] = {"status": "ok", "category": rec["assignments"]["category"],
                                       "entity": rec["assignments"]["entity"]}
        if rec.get("prompt_sha256"):
            checked += 1
            matches += rec["prompt_sha256"] == llm.world_prompt_sha256(w)
    submission = {
        "schema_version": "1.0", "benchmark": "h1-v2-test", "model": args.model,
        "date": args.date or datetime.now(timezone.utc).date().isoformat(),
        "h1bench_version": __version__, "input_sha256": sha256_bytes(raw),
        "prompt_files_sha256": llm.prompt_files_sha256(),
        "prompt_world_matches": {"matching_reference": matches, "checked": checked},
        "n_worlds": len(worlds), "n_answered": sum(1 for p in predictions.values() if p["status"] == "ok"),
        "predictions": predictions,
    }
    out = Path(args.out)
    out.write_text(json.dumps(submission, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"wrote {out}: {submission['n_answered']}/{len(worlds)} worlds answered; "
          f"prompt matches reference on {matches}/{checked} checked worlds")
    print(f"input_sha256 {submission['input_sha256']}")
    print(f"next: put it at submissions/<team>-<model>/submission.json and open a pull request")
    return 0


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="h1bench", description=__doc__)
    p.add_argument("--version", action="version", version=f"h1bench {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("smoke", help="offline check on a tiny bundled development subset (seconds)")
    s.set_defaults(fn=cmd_smoke)

    s = sub.add_parser("baselines", help="run the public baselines (dev: score them; test: write predictions)")
    s.add_argument("--split", choices=["dev", "test"], default="dev")
    s.add_argument("--dataset", choices=["v2-pilot", "v1", "all"], default="all")
    s.add_argument("--draws", type=int, default=ev.DRAWS)
    s.add_argument("--by-family", action="store_true")
    s.add_argument("--out-dir", default=".")
    s.add_argument("--json", help="dev only: also write the aggregate scores here")
    s.set_defaults(fn=cmd_baselines)

    s = sub.add_parser("run", help="run an OpenAI-compatible chat model and write a predictions JSONL file")
    s.add_argument("--split", choices=["dev", "test"], required=True)
    s.add_argument("--dataset", choices=["v2-pilot", "v1", "all"], default="v2-pilot", help="dev only")
    s.add_argument("--base-url", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--api-key-env", default="OPENAI_API_KEY", help="name of the environment variable holding the key")
    s.add_argument("--concurrency", type=int, default=4)
    s.add_argument("--out")
    s.add_argument("--limit", type=int, help="run only the first N worlds")
    s.add_argument("--timeout", type=float, default=llm.DEFAULT_TIMEOUT_S, help="per-request timeout in seconds")
    s.add_argument("--max-tokens", type=int, default=llm.DEFAULT_MAX_TOKENS)
    s.add_argument("--no-response-format", action="store_true", help="do not send response_format=json_object")
    s.add_argument("--retry-failed", action="store_true", help="re-run worlds whose last record failed")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("score", help="score predictions on the labeled development data")
    s.add_argument("--split", choices=["dev", "test"], required=True)
    s.add_argument("--dataset", choices=["v2-pilot", "v1", "all"], default="all")
    s.add_argument("--draws", type=int, default=ev.DRAWS)
    s.add_argument("--json", help="also write the aggregate scores here")
    s.add_argument("predictions")
    s.set_defaults(fn=cmd_score)

    s = sub.add_parser("make-submission", help="validate test predictions and write submission.json")
    s.add_argument("predictions")
    s.add_argument("--model", required=True, help="model name and version")
    s.add_argument("--out", default="submission.json")
    s.add_argument("--date", help="YYYY-MM-DD (default: today, UTC)")
    s.add_argument("--allow-missing", action="store_true")
    s.set_defaults(fn=cmd_make_submission)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
