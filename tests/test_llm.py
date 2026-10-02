import json

from h1bench import evaluate as ev, llm


def world():
    worlds, _ = ev.load_test_inputs()
    return worlds[0]


def ids_json(w, groups_cat, groups_ent):
    return json.dumps({"category_groups": groups_cat, "entity_groups": groups_ent})


def all_in_one(w):
    ms = [f"M{i}" for i in range(1, len(w["mentions"]) + 1)]
    return ids_json(w, [ms], [[m] for m in ms])


def test_parse_accepts_prose_when_format_not_honored():
    text = 'Sure: {"category_groups": [["M1"]], "entity_groups": [["M1"]]} thanks'
    assert llm.parse_partitions(text, response_format_honored=False)["category_groups"] == [["M1"]]


def test_parse_strict_when_format_honored():
    try:
        llm.parse_partitions("prose {}", response_format_honored=True)
    except llm.PartitionParseError:
        return
    raise AssertionError("expected a parse error")


def test_validate_rejects_missing_duplicate_and_extra_ids():
    expected = {"M1", "M2"}
    for obj in (
        {"category_groups": [["M1"]], "entity_groups": [["M1"], ["M2"]]},
        {"category_groups": [["M1", "M1"], ["M2"]], "entity_groups": [["M1"], ["M2"]]},
        {"category_groups": [["M1"], ["M2"], ["M3"]], "entity_groups": [["M1"], ["M2"]]},
        {"category_groups": [["M1"], ["M2"]]},
    ):
        try:
            llm.validate_partitions(obj, expected)
        except llm.PartitionParseError:
            continue
        raise AssertionError(obj)


def test_run_world_ok_and_maps_to_real_ids():
    w = world()
    rec = llm.run_world(lambda m: llm.ChatReply(all_in_one(w), {"total_tokens": 5}, True), w, model="m")
    assert rec["status"] == "ok" and rec["usage"] == {"total_tokens": 5}
    real = {m["mention_id"] for m in w["mentions"]}
    assert set(rec["assignments"]["category"]) == real == set(rec["assignments"]["entity"])
    assert len(set(rec["assignments"]["category"].values())) == 1


def test_repair_then_success_sums_usage():
    w = world()
    calls = []

    def chat(messages):
        calls.append(len(messages))
        if len(calls) == 1:
            return llm.ChatReply("not json", {"total_tokens": 2}, True)
        return llm.ChatReply(all_in_one(w), {"total_tokens": 3}, True)

    rec = llm.run_world(chat, w, model="m")
    assert rec["status"] == "ok" and calls == [2, 4] and rec["usage"]["total_tokens"] == 5


def test_three_bad_replies_fail_parse_and_score_unresolved():
    w = world()
    rec = llm.run_world(lambda m: llm.ChatReply("nope", {}, True), w, model="m")
    assert rec["status"] == "failed_parse" and rec["assignments"] is None


def test_timeout_becomes_failed_api():
    def chat(_):
        raise llm.ApiFailure("timeout")

    rec = llm.run_world(chat, world(), model="m")
    assert rec["status"] == "failed_api" and rec["error"] == "timeout"


def test_run_worlds_resumes(tmp_path):
    worlds, _ = ev.load_test_inputs()
    ws = worlds[:5]
    calls = []

    def chat(messages):
        calls.append(1)
        n = messages[1]["content"].count('"id": "M')
        ms = [f"M{i}" for i in range(1, n + 1)]
        return llm.ChatReply(json.dumps({"category_groups": [ms], "entity_groups": [ms]}), {}, True)

    out = tmp_path / "p.jsonl"
    c1 = llm.run_worlds(chat, ws[:3], out, model="m", concurrency=3)
    c2 = llm.run_worlds(chat, ws, out, model="m", concurrency=3)
    assert c1["ok"] == 3 and c2["ok"] == 2 and c2["skipped"] == 3 and len(calls) == 5
    assert len(ev.read_records(out)) == 5


def test_prompt_hash_is_stable():
    assert llm.prompt_files_sha256() == "706e7c5b6240a2522e990e1b20cc553f3c525a8d38e78539c8b7069d419eac6e"
