"""Run any OpenAI-compatible chat model on H1 worlds and write a predictions file.

Prompt text, mention relabeling (M1..Mn in input order), response parsing and the
repair policy follow the paper's runner. The provider-specific key rotation, budget
guard and circuit breaker are not included. A world whose requests keep failing, or
whose reply never parses, becomes an unresolved record (``failed_api`` or
``failed_parse``); the scorer treats every mention of it as a singleton.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Callable

TEMPERATURE = 0
REPAIR_RETRIES = 2  # up to 2 repair turns after the first parse failure -> 3 tries
REPAIR_ECHO_MAX_CHARS = 2000
RAW_CONTENT_TRUNCATE_CHARS = 20_000
API_RETRY_ATTEMPTS = 6
BACKOFF_START_S = 20.0
BACKOFF_CAP_S = 300.0
DEFAULT_MAX_TOKENS = 32768
DEFAULT_TIMEOUT_S = 300.0


# ---------------------------------------------------------------- prompts

@lru_cache(maxsize=None)
def _prompt_text(name: str) -> str:
    return resources.files("h1bench").joinpath("prompts", name).read_text(encoding="utf-8")


def prompt_files_sha256() -> str:
    """Hash of the three prompt files (system, user template, repair template)."""
    h = hashlib.sha256()
    for name in ("system_prompt.txt", "user_prompt_template.txt", "repair_prompt_template.txt"):
        h.update(name.encode() + b"\0" + _prompt_text(name).encode("utf-8") + b"\0")
    return h.hexdigest()


def relabel_world(world: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Return (llm_mentions, m_to_real). Mentions get ids M1..Mn in input order."""
    llm_mentions: list[dict[str, Any]] = []
    m_to_real: dict[str, str] = {}
    for index, mention in enumerate(world["mentions"], start=1):
        placeholder = f"M{index}"
        m_to_real[placeholder] = mention["mention_id"]
        row: dict[str, Any] = {"id": placeholder, "frame": mention["frame"]}
        if "descriptor" in mention:
            row["descriptor"] = mention["descriptor"]
        llm_mentions.append(row)
    return llm_mentions, m_to_real


def build_initial_messages(llm_mentions: list[dict[str, Any]]) -> list[dict[str, str]]:
    mentions_json = json.dumps(llm_mentions, sort_keys=True, ensure_ascii=False, indent=2)
    user = _prompt_text("user_prompt_template.txt").format(mention_count=len(llm_mentions), mentions_json=mentions_json)
    return [{"role": "system", "content": _prompt_text("system_prompt.txt")}, {"role": "user", "content": user}]


def build_repair_prompt(error: str, mention_count: int) -> str:
    return _prompt_text("repair_prompt_template.txt").format(error=error, mention_count=mention_count)


def world_prompt_sha256(world: dict[str, Any]) -> str:
    """Hash of the exact initial prompt pair for one world (same definition as the paper's records)."""
    llm_mentions, _ = relabel_world(world)
    payload = json.dumps(build_initial_messages(llm_mentions), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------- parsing

class PartitionParseError(ValueError):
    """Raised with a short, model-facing reason a response was rejected."""


def extract_first_balanced_json_object(text: str) -> str:
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]
        start = text.find("{", start + 1)
    raise PartitionParseError("no balanced JSON object found in response")


def parse_partitions(content: str | None, *, response_format_honored: bool) -> dict[str, Any]:
    if content is None:
        raise PartitionParseError("empty response content")
    candidate = content
    if not response_format_honored:
        try:
            candidate = extract_first_balanced_json_object(content)
        except PartitionParseError:
            candidate = content
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise PartitionParseError(f"response is not valid JSON: {exc}") from None
    if not isinstance(obj, dict):
        raise PartitionParseError("response JSON is not an object")
    return obj


def validate_partitions(obj: dict[str, Any], expected_ids: set[str]) -> dict[str, list[list[str]]]:
    if set(obj) != {"category_groups", "entity_groups"}:
        raise PartitionParseError(
            f"response must have exactly keys category_groups and entity_groups, got {sorted(obj)}"
        )
    result: dict[str, list[list[str]]] = {}
    for key in ("category_groups", "entity_groups"):
        groups = obj[key]
        if not isinstance(groups, list) or not all(isinstance(g, list) for g in groups):
            raise PartitionParseError(f"{key} must be a list of lists")
        flat: list[str] = []
        normalized_groups: list[list[str]] = []
        for group in groups:
            if not group:
                raise PartitionParseError(f"{key} contains an empty group")
            normalized_group = []
            for item in group:
                if not isinstance(item, str):
                    raise PartitionParseError(f"{key} contains a non-string mention id: {item!r}")
                flat.append(item)
                normalized_group.append(item)
            normalized_groups.append(normalized_group)
        if len(flat) != len(set(flat)):
            dupes = sorted({m for m in flat if flat.count(m) > 1})
            raise PartitionParseError(f"{key} repeats mention id(s): {dupes}")
        seen = set(flat)
        missing = expected_ids - seen
        extra = seen - expected_ids
        if missing or extra:
            raise PartitionParseError(f"{key} id mismatch: missing={sorted(missing)} extra={sorted(extra)}")
        result[key] = normalized_groups
    return result


def groups_to_assignment(groups: list[list[str]], m_to_real: dict[str, str]) -> dict[str, str]:
    assignment: dict[str, str] = {}
    for index, group in enumerate(groups, start=1):
        for placeholder in group:
            assignment[m_to_real[placeholder]] = f"cluster_{index:06d}"
    return assignment


# ---------------------------------------------------------------- one world

@dataclass
class ChatReply:
    content: str | None
    usage: dict[str, Any]
    response_format_honored: bool


class ApiFailure(Exception):
    """Every API attempt for a request failed (timeouts, 5xx, connection errors)."""


ChatFn = Callable[[list[dict[str, str]]], ChatReply]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(world_id: str, model: str, status: str, started_at: str, elapsed: float, *, raw: str | None,
            usage: dict[str, Any], prompt_sha: str, error: str | None,
            assignments: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "world_id": world_id, "model": model, "status": status, "assignments": assignments,
        "raw_content": raw[:RAW_CONTENT_TRUNCATE_CHARS] if isinstance(raw, str) else raw,
        "usage": usage, "latency_s": round(elapsed, 3), "started_at": started_at, "completed_at": _now(),
        "prompt_sha256": prompt_sha, "error": error,
    }


def run_world(chat: ChatFn, world: dict[str, Any], *, model: str) -> dict[str, Any]:
    """Resolve one world. Never raises for API or parse failures; returns a JSONL-ready record."""
    world_id = world["world_id"]
    started_at = _now()
    t0 = time.monotonic()
    llm_mentions, m_to_real = relabel_world(world)
    expected = set(m_to_real)
    messages = build_initial_messages(llm_mentions)
    prompt_sha = world_prompt_sha256(world)
    usage: dict[str, Any] = {}
    raw: str | None = None
    error: str | None = None
    for attempt in range(REPAIR_RETRIES + 1):
        try:
            reply = chat(messages)
        except ApiFailure as exc:
            return _record(world_id, model, "failed_api", started_at, time.monotonic() - t0, raw=raw, usage=usage,
                           prompt_sha=prompt_sha, error=str(exc), assignments=None)
        raw = reply.content
        for field, value in reply.usage.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage[field] = usage.get(field, 0) + value
        try:
            groups = validate_partitions(
                parse_partitions(reply.content or "", response_format_honored=reply.response_format_honored), expected)
        except PartitionParseError as exc:
            error = str(exc)
            if attempt < REPAIR_RETRIES:
                messages = messages + [
                    {"role": "assistant", "content": (reply.content or "")[:REPAIR_ECHO_MAX_CHARS]},
                    {"role": "user", "content": build_repair_prompt(error, len(expected))},
                ]
                continue
            return _record(world_id, model, "failed_parse", started_at, time.monotonic() - t0, raw=raw, usage=usage,
                           prompt_sha=prompt_sha, error=error, assignments=None)
        assignments = {
            "category": groups_to_assignment(groups["category_groups"], m_to_real),
            "entity": groups_to_assignment(groups["entity_groups"], m_to_real),
        }
        return _record(world_id, model, "ok", started_at, time.monotonic() - t0, raw=raw, usage=usage,
                       prompt_sha=prompt_sha, error=None, assignments=assignments)
    raise AssertionError("unreachable")


# ---------------------------------------------------------------- OpenAI-compatible transport

def make_openai_chat(*, base_url: str, model: str, api_key_env: str, timeout: float = DEFAULT_TIMEOUT_S,
                     max_tokens: int = DEFAULT_MAX_TOKENS, send_response_format: bool = True,
                     api_retries: int = API_RETRY_ATTEMPTS, backoff_start: float = BACKOFF_START_S) -> ChatFn:
    """Build a ChatFn for any OpenAI-compatible endpoint. Needs the optional ``openai`` package."""
    try:
        import openai
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("the runner needs the optional dependency: pip install 'h1bench[openai]'") from exc
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise SystemExit(f"environment variable {api_key_env} is empty or not set")
    client = openai.OpenAI(base_url=base_url, api_key=api_key, timeout=timeout, max_retries=0)
    caps = {"temperature": True, "response_format": send_response_format}
    lock = threading.Lock()

    def chat(messages: list[dict[str, str]]) -> ChatReply:
        last_error = "no attempt made"
        for attempt in range(1, api_retries + 1):
            body: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens}
            with lock:
                use_temp, use_rf = caps["temperature"], caps["response_format"]
            if use_temp:
                body["temperature"] = TEMPERATURE
            if use_rf:
                body["response_format"] = {"type": "json_object"}
            try:
                resp = client.chat.completions.create(**body)
            except openai.BadRequestError as exc:
                text = str(exc).lower()
                with lock:
                    if use_temp and "temperature" in text:
                        caps["temperature"] = False
                        continue
                    if use_rf and "response_format" in text:
                        caps["response_format"] = False
                        continue
                last_error = f"HTTP 400: {str(exc)[:300]}"
                break
            except (openai.APITimeoutError, openai.APIConnectionError, openai.InternalServerError,
                    openai.RateLimitError) as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
                if attempt < api_retries:
                    time.sleep(min(BACKOFF_CAP_S, backoff_start * 2 ** (attempt - 1)))
                continue
            except openai.APIError as exc:
                last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
                break
            choice = (resp.choices or [None])[0]
            content = choice.message.content if choice is not None else None
            usage = resp.usage.model_dump() if getattr(resp, "usage", None) is not None else {}
            return ChatReply(content=content, usage=usage, response_format_honored=caps["response_format"])
        raise ApiFailure(last_error)

    return chat


# ---------------------------------------------------------------- batch driver

def run_worlds(chat: ChatFn, worlds: list[dict[str, Any]], out_path: Path, *, model: str, concurrency: int = 4,
               retry_failed: bool = False, progress: Callable[[int, int, dict[str, Any]], None] | None = None
               ) -> dict[str, int]:
    """Run worlds with a thread pool and append one JSONL record per finished world.

    Resumable: a world with a final record (``ok``, or a failure unless ``retry_failed``) is skipped.
    """
    from h1bench.evaluate import read_records

    existing = read_records(out_path)
    todo = [w for w in worlds
            if (w["world_id"] not in existing)
            or (retry_failed and existing[w["world_id"]].get("status") != "ok")]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {"ok": 0, "failed_api": 0, "failed_parse": 0, "skipped": len(worlds) - len(todo)}
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool, open(out_path, "a", encoding="utf-8") as fh:
        futures = [pool.submit(run_world, chat, w, model=model) for w in todo]
        for future in as_completed(futures):
            record = future.result()
            fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            counts[record["status"]] += 1
            done += 1
            if progress:
                progress(done, len(todo), record)
    return counts
