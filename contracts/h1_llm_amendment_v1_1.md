> Public copy of the private LLM amendment (frozen before the runs). It documents how the paper's two models were run. Provider, key and budget details describe the paper's runs; the public runner (`h1bench run`) drops key rotation, budget and circuit-breaker code. Module and file names refer to the private research repository.

# H1 LLM linker amendment (v1.1)

## Purpose

The frozen H1 hidden-identity benchmark (`docs/research/h1_benchmark_contract.md`)
so far reports only deterministic rule baselines. This amendment adds the
first two learned comparators -- two hosted LLMs used directly as linkers --
scored on the same frozen worlds with the same unchanged scorer. It changes
no benchmark data: `inputs.json`, `labels.json`, the generator, the schema,
the rule baselines, the worker, the scorer, and the v1 freeze manifest are
untouched. This document and its own new freeze manifest
(`evaluation/hidden_identity/llm_freeze_manifest.json`) cover only the new
LLM-linker code, prompts, and parameters.

## Models, providers, and parameters

Both models are served by OpenRouter:

| slug | model id | provider | openrouter order |
| --- | --- | --- | --- |
| `glm_5_3_flash` | `z-ai/glm-5.3-flash` | OpenRouter | `["modal"]` |
| `deepseek_v4_1_flash` | `deepseek/deepseek-v4.1-flash` | OpenRouter | `["together"]` |

Authenticated with a single key (`OPENROUTER_API_KEY`). Both models started
on NVIDIA; both moved off it, for separate measured reasons, before any
benchmark call:

- **DeepSeek**: NVIDIA returned HTTP 504 after the full 300s wait on every
  one of 3 NVIDIA keys for `deepseek-ai/deepseek-v4.1-flash` (confirmed in
  this amendment's own train-split pilot: 0 of 3 pilot calls completed on
  NVIDIA within two 300s attempts each). The same model through OpenRouter
  responded in seconds. DeepSeek moved to OpenRouter first.
- **GLM**: NVIDIA served `z-ai/glm-5.3-flash` on a plain (buffered) request
  under load, but calls that ran past roughly 300s also came back as HTTP
  504, observed twice in a train-split pilot. NVIDIA was switched to
  server-sent-event streaming for this reason (below); that follow-up smoke
  test avoided the 504, but GLM still took 695s for one train world (8,042
  completion tokens, 33k reasoning characters) and, on another world,
  exhausted the entire 8,192-token completion budget three times in a row
  with empty content (all of it consumed by reasoning before any JSON
  content was produced) -- 2,223s spent with nothing usable. Neither the
  latency nor the empty-content failure was acceptable, so GLM moved to
  OpenRouter as well, with a larger completion budget (below).

NVIDIA's streaming transport is still defined in `config.PROVIDERS["nvidia"]`
and implemented in `client.py` (kept, and still covered by tests, in case a
model returns to it), but no current model uses it.

Requested parameters on OpenRouter: `temperature=0`,
`response_format={"type": "json_object"}`, `max_tokens=32768`. The budget was
raised from an initial 8,192: both models' first pilot replies came back
with empty content because reasoning tokens alone consumed the whole
budget before any JSON content was generated; 32768 leaves real headroom.
If a model's API rejects `temperature=0`, the run drops the parameter
(provider default applies) and records the accepted setting per world. If a
model's API rejects `response_format`, the run falls back to extracting the
first balanced JSON object from the raw message content.

OpenRouter calls additionally set `usage: {"include": true}` (so token
counts and, when available, per-call cost come back in `usage`) and
`provider: {"require_parameters": true, "order": [...], "allow_fallbacks": true}`,
with a separate pinned `order` per model (table above). `require_parameters`
makes OpenRouter only route to an upstream host that actually honors
`temperature`/`response_format`, instead of silently dropping them and
picking a host that ignores the request. `order` pins each model's
preferred upstream host for consistency: DeepSeek's host ("together") was
already confirmed serving it correctly in the pilot; GLM's host ("modal")
was chosen by checking `GET /api/v1/models/z-ai/glm-5.3-flash/endpoints` on
2026-09-27 and picking the lowest measured p50 latency (~465ms) among hosts
that list both `response_format` and `temperature` as supported parameters
(Together also qualified, at ~554ms). `allow_fallbacks: true` keeps the call
working if the pinned host is unavailable rather than failing outright.
Either way, the upstream host actually used is never assumed: each
OpenRouter response may carry a top-level `provider` field naming it (e.g.
"Novita" or "Together"), recorded per call as `upstream_provider` and
reported in aggregate.

`glm-5.3-flash` is a reasoning model: its reasoning text (`reasoning_content`
on NVIDIA, `reasoning` on OpenRouter -- whichever field is present, per
provider) is never stored in full, only its character length, alongside
token usage from the API's `usage` block.

### NVIDIA transport: streaming (defined, currently unused)

While GLM was still on NVIDIA, calls were switched to server-sent-event
streaming (`stream: true`, `stream_options: {"include_usage": true}`) after
buffered (non-streaming) calls that ran past roughly 300s came back as HTTP
504. Streaming avoided the 504 in the follow-up smoke test. This was a
transport change only: content is reassembled from `delta.content` chunks,
reasoning length from `delta.reasoning_content`/`delta.reasoning`, usage
from whichever chunk carries it (normally the last one), and
`finish_reason` from the last choice that sets one. Non-`data:` lines (SSE
comments/keepalives) and blank lines are ignored; a `data: [DONE]` line ends
the stream normally, and a stream that ends without one (or a chunk with
unparseable JSON) is treated as a transient network failure, retried like
any other. NVIDIA's per-call timeout for this path is
`httpx.Timeout(connect=30, read=600, write=60, pool=60)` (`read` is the max
gap between bytes) plus an overall 1200s wall-clock cap per attempt. This
transport remains defined and tested but is not used by either current
model, since GLM subsequently moved to OpenRouter for the latency/empty-
content reasons above.

### Concurrency, rate limits, and the budget guard

Per-model concurrency defaults: `glm_5_3_flash` 16, `deepseek_v4_1_flash` 16
(`--concurrency-per-model` overrides either; `--concurrency` is the fallback
for any model without its own override). OpenRouter requests-per-minute
default: 120 (single key); `--rpm-per-key` overrides it if given. A 429 from
OpenRouter cools down that key and retries, the same as any other provider.

A budget guard stops the run before spend runs away: cumulative
`usage.cost` is summed across every record (not deduplicated by world, so a
retried world's earlier billed attempts still count) in **both** models'
predictions JSONL files, including from prior runs, every time a new record
is written. Once that sum exceeds $20.00, no new world is dispatched,
in-flight calls are allowed to finish, and the process exits with a
dedicated code (`EXIT_BUDGET_EXHAUSTED = 6`). The running total and the
threshold are written into `status.json` and logged at every ~30s
heartbeat. All of the above -- providers, per-model order, streaming policy,
timeouts, concurrency, and the budget threshold -- are recorded in
`build_freeze_config()`. These defaults, and the pilot calls that informed
them (train-split only, format-checked, never scored, labels never read),
are recorded above.

## Input

Each call receives exactly `evaluation.hidden_identity.runner._sanitize_world(world)`
for one world -- the same `{world_id, mentions: [{mention_id, frame,
descriptor?}]}` shape the deterministic rule baselines receive. No
`scenario_family`, `split`, or label field is ever sent. Mention ids are
relabeled `M1..Mn` in input order before the call (to reduce copy errors) and
mapped back to the real opaque ids after parsing.

## Output contract and recorded methods

One call per world returns a single JSON object:
`{"category_groups": [[id, ...], ...], "entity_groups": [[id, ...], ...]}`,
each partition covering every mention id exactly once. Category and entity
follow the contract's definitions (finding type + organ-level site + side
(laterality) for category, including explicitly-referenced
absent/uncertain/negated mentions; individual lesion identity for entity,
with distinct simultaneous same-key lesions as different entities, a
resolved-then-recurring finding as a new entity, and diffuse/innumerable
sets as one group).

Two methods are recorded per model:

- `<slug>_category_partition`: the `category_groups` partition as the single assignment.
- `<slug>_entity_partition`: the `entity_groups` partition as the single assignment.

Both are scored on both axes by the unchanged `score_world`, exactly like
the existing rule baselines (a method optimized for one construct is still
scored against the other).

## Failure and repair policy

A response is validated: both keys present, ids exactly `M1..Mn`, each
appearing exactly once per partition. An invalid response gets up to 2
repair retries (the invalid content, cut to its first 2,000 characters, plus a short
error message is resent; one pilot repair that echoed a long reply in full reached
67k prompt tokens). Recorded token counts and cost are summed over every call for
a world, repairs included, and the budget guard uses those sums.
If still invalid after 2 repairs, the world is recorded `failed_parse`.
Network/HTTP failures (429, 5xx, timeout, connection error) are retried
with key rotation and backoff; if a world's calls never succeed, it is
recorded `failed_api`. At scoring time, any world without an `ok` record
(never attempted, `failed_api`, or `failed_parse`) is scored with an
all-`None` (fully unresolved) assignment on both axes, and failure counts
are reported alongside the scores. No success threshold is set for either
model in advance; positive, neutral, and negative outcomes are all
reportable.

## Predeclared contrasts and estimands

For each model and each recorded partition, paired world-cluster bootstrap
contrasts (seed 42, 10,000 draws, same family-stratified method as the v1
contrasts) against the existing rule baselines:

1. `<slug>_category_partition` minus `exact_normalized_key`, and minus
   `current_compatibility_linker`, on category `split_pair_rate` and
   `merge_pair_rate`, over the held-out granularity families
   (`anatomy_organ_lobe_segment`, `anatomy_raw_vs_hierarchy`).
2. `<slug>_entity_partition` minus `exact_normalized_key`, and minus
   `descriptor_exact_normalized_key_v1`, on entity `merge_pair_rate` and
   `split_pair_rate`, over the held-out descriptor families
   (`descriptor_present_same_key`, `descriptor_absent_same_key`).
3. The same four left/right pairs, over all 8 test families, on the
   headline B-cubed F1 (category F1 for the category-side pairs, entity F1
   for the entity-side pairs).

Rule-baseline per-world scores are loaded from the frozen
`outputs/hidden_identity/h1_v1/results.json`, never recomputed.

## Split order and the pilot

Worlds are processed in a fixed order: all test worlds first (both models),
then dev, then train. The `pilot` subcommand is format-only: it runs without
the freeze guard, uses only TRAIN-split worlds, writes to a separate
`outputs/hidden_identity/h1_llm_v1/pilot/` directory, and never reads
`labels.json`. It checks HTTP success, JSON validity, and latency/token
counts -- it does not compute or report any accuracy score.

Frozen at: (filled by the `freeze` subcommand)

## Provider change during the run (2026-09-27)

The run started on OpenRouter under the first freeze (manifest kept as
`llm_freeze_manifest_segment1_openrouter.json`, frozen 15:02:53 UTC). At about
15:18 UTC the OpenRouter key hit its monthly spending limit and every call
returned HTTP 403. By then 402 DeepSeek and 208 GLM test worlds had finished
with valid output; no labels had been read and nothing had been scored.

The remaining worlds run on NVIDIA's free endpoints under a second freeze
(`llm_freeze_manifest.json`): `deepseek-ai/deepseek-v4.1-flash` and
`z-ai/glm-5.3-flash`, three-key rotation, streaming, `max_tokens` 32768 (same
as OpenRouter), longer stream timeouts (read 1200 s, wall-clock cap 2400 s),
and 24 concurrent calls per model. A streaming check before the switch got
valid replies from DeepSeek on NVIDIA in about 268 s. Prompts, input fields,
parsing, repair policy, recorded methods and scoring do not change. Each
prediction record keeps its own `provider` field, so results are reported for
each model overall and split by provider.

### DeepSeek on NVIDIA: JSON mode off (2026-09-27, ~16:00 UTC)

In the first NVIDIA segment every DeepSeek reply had empty content: the model
stopped after about 60 reasoning tokens (12 test worlds recorded `failed_parse`).
A direct probe on one train world showed the cause: with
`response_format=json_object` NVIDIA's DeepSeek returns no content; without it,
the same request returns a valid JSON object after about 8,400 reasoning tokens.
DeepSeek on NVIDIA therefore runs without `response_format`, and its reply is
parsed with the first-balanced-JSON-object fallback already declared above.
GLM keeps `response_format`. The `failed_parse` worlds are retried under the
third freeze; each record's `response_format_honored` field shows which mode it used.

## Interim look at test labels (2026-09-27, ~18:05 UTC)

With 421 test worlds finished by both models, the orchestrator scored those
worlds against the labels as a sanity check. Nothing in the frozen LLM setup
changed afterwards. The check found a benchmark design property that affects
interpretation: every v1 test world has exactly one gold category, so a
one-group-per-world predictor scores category B-cubed F1 = 1.000 in all eight
test families and no method can make a category merge error. The final report
therefore adds two trivial label-free baselines beside every method:
one group per world and one group per mention. A v2 benchmark with several
categories per world is being built and will be frozen before any method is
scored on it.
