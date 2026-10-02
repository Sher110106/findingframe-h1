> Public copy of the private v2 contract. Redactions are listed in `contracts/REDACTIONS.md`. Module and file names refer to the private research repository; the public package is `h1bench`.

# H1 synthetic hidden-identity benchmark contract (v2)

## Purpose

v1 (`docs/research/h1_benchmark_contract.md`, frozen 2026-09-2x) put exactly one gold category in every
test world. A predictor that puts every mention of a world into one group therefore scores a perfect
category B-cubed F1 on every v1 test world, and category *merge* pairwise error can never occur there at
all -- v1's test-family result (compatibility linker ties exact key on category split error) cannot
distinguish a linker that over-splits from one that over-merges, because merging was never penalized.
This flaw was found reviewing the v1 interim look on 2026-09-27. v2 is a new, separate benchmark release
that fixes it: every world holds 2-3 gold categories, a target plus one or two authored near-miss
distractor categories that share surface wording, organ, side, or finding type with the target, so
over-merging is penalized exactly as much as over-splitting. **v1's result must now be read alongside
v2's**; neither supersedes the other, since they test complementary failure modes (v1: does the linker
avoid splitting one continuing category across granularity/report-order changes; v2: does the linker
avoid merging distinct-but-similar categories together, while still not splitting one category across its
own granularity variation).

v2 is an artificial construct-validity experiment, not clinical validation, exactly as v1. No success
threshold is asserted after outcomes: report effect sizes and 95% confidence intervals under the registry
below; positive, neutral, and negative outcomes are all publishable.

## Construct definitions (unchanged from v1)

Category = the production finding type plus organ-level site and laterality (the same composite key
`fact_graph.frame_linker` and `evaluation.hidden_identity.baselines.exact_normalized_key`/
`current_compatibility_linker` use). Entity = an individual lesion. Different findings, organs, or sides
have different categories. Same-category simultaneous same-location lesions can have different entities;
an episode can reuse a category/key after a resolved prior episode but receive a new entity ID. Observable
morphology descriptors are generic evidence present in authored text, not unique aliases. Absent/uncertain/
negated statements stay in the category trajectory when they explicitly refer to it. See
`docs/research/h1_benchmark_contract.md` for the full original definitions; v2 changes none of them.

## Isolation

Identical to v1: `inputs.json` is the only linker-visible dataset (opaque `world_id`, `scenario_family`,
fixed `split`, and mentions with opaque `mention_id` and the same frame-field allowlist as v1 --
`evaluation.hidden_identity.schema.FRAME_FIELDS`, reused unmodified). No patient ID, category ID, entity
ID, or label-derived field appears in `inputs.json`; `evaluation.hidden_identity.v2.runner_v2._validate_public_inputs`
runs the same forbidden hidden-label-field scan as v1's `runner._validate_public_inputs` before any
prediction. `labels.json` is a separate sealed scorer input, validated with the unchanged v1
`schema.validate_labels`/`schema.validate_label_alignment`. Before the recorded freeze, the benchmark must
not be scored: public inputs, labels, generator, config, this contract, and release files must be frozen
and their hashes recorded (`evaluation/hidden_identity/v2/freeze_manifest_v2.json`). A further private analysis file (a per-world design flag for one family) is withheld.

## Families, sizes, seed

Eight scenario families, all `split="test"` (v2 is evaluation-only: no train/dev tuning split, unlike v1).
50 structurally varied worlds per family (400 worlds), plus a separate 3-worlds-per-family pilot split (24
worlds, different seed prefix, family name suffixed `_pilot`, stored under `split="train"` only because the
schema functions this package calls -- v1's `schema.validate_labels`/`validate_label_alignment` and this
package's own `schema_v2.validate_inputs_v2` -- restrict `split` to `{train, dev, test}` and `train` is
otherwise unused by v2's all-test design; see `schema_v2.py`). Pilot worlds are format/LLM-smoke-test-only
and are excluded from every estimate by `runner_v2` regardless of the `split` field. Worlds hold 8-14
mentions across 3-5 reports (wider than v1's frozen 6-8 bound -- see `schema_v2.py` for why v1's `schema.py`
could not be reused for input validation, and what stayed identical). Generation is deterministic. The seed, the identifier-hash material and the generator are withheld.
Family list and per-family target/distractor design: `DATA_CARD.md`.

## Predeclared analysis registry

Methods: `one_group_per_world`, `one_group_per_mention` (trivial, label-free, design-validation only --
scored pre-freeze), `raw_surface_equality`, `exact_normalized_key`, `current_compatibility_linker`,
`descriptor_exact_normalized_key_v1`, the v1 ablations (`no_anatomy_hierarchy`, `strict_laterality`,
`raw_anatomy`; `descriptor_removed`, `input_report_order_reversed`, `tied_event_order_reversed` also run
via the unmodified v1 worker for completeness), `oracle_ceiling` (scorer only), and, once the LLM freeze
below is reviewed and run, the two LLM partitions per model (`deepseek_v4_1_flash`, `glm_5_3_flash`;
`category_partition` and `entity_partition`). All ten non-trivial rule methods are the frozen v1
implementations in `evaluation/hidden_identity/baselines.py`, invoked through the unmodified v1
`evaluation.hidden_identity.worker` exactly as v1 uses them -- no v2-specific rule-linker code exists.

Outcomes: category and entity B-cubed precision/recall/F1, `split_pair_rate`, `merge_pair_rate`, per family
and family-macro (`evaluation.hidden_identity.scorer.score_world`/`aggregate_worlds`, unmodified). World-
cluster bootstrap: seed 42, 10,000 draws, stratified by family (`scorer.paired_world_bootstrap`, unmodified).

Predeclared contrasts:
- `current_compatibility_linker` minus `exact_normalized_key` on category F1, `split_pair_rate`, and
  `merge_pair_rate`, over (a) all eight main families and (b) the two granularity families
  (`granularity_with_laterality_distractor`, `granularity_with_organ_distractor`) alone. Implemented in
  `runner_v2.CONTRASTS`.
- Each LLM model's `category_partition` minus `current_compatibility_linker` and minus
  `exact_normalized_key` on category F1/`split_pair_rate`/`merge_pair_rate`.
- Each LLM model's `entity_partition` minus `exact_normalized_key` and minus
  `descriptor_exact_normalized_key_v1` on entity `merge_pair_rate`/`split_pair_rate` (restricted to the
  families with real entity structure: `simultaneous_distinct_with_distractor`,
  `descriptor_pair_with_distractor`, `episode_reuse_with_distractor`, and the two granularity families,
  each of whose target category has a single, granularity-varying entity) and on entity F1 (all families).
  The LLM contrasts are computed by `evaluation/hidden_identity/v2/score_llm_v2.py` (not `runner_v2`, which
  only runs the ten rule methods and the two trivial baselines), since `llm_linker.scoring`'s contrast names
  are v1-family-specific.

No post-outcome threshold selection. No success threshold is asserted; all outcomes (positive, neutral, or
negative) are reportable, exactly as v1.

## Design validation performed before freeze (labels + trivial predictors only)

Computed and recorded in `data_card.md`: categories/world, entities/world, and the scores of
`one_group_per_world`/`one_group_per_mention` under the unmodified v1 scorer, plus raw surface-word overlap
statistics computed directly from `inputs.json` (casefolded exact `finding_surface` string match), plus a
raw-slot-tuple recoverability check (below). No `raw_surface_equality`, `exact_normalized_key`,
`current_compatibility_linker`, descriptor comparator, or LLM was run on v2 before freeze.

**Limitation: slot-tuple recoverability is uneven across families.** Grouping mentions by the exact
`(finding_type, anatomy, laterality)` raw frame-slot tuple (not the production-normalized linking view)
exactly reproduces the gold category partition in 300/400 test worlds -- 100% in six families
(`descriptor_pair_with_distractor`, `episode_reuse_with_distractor`, `laterality_pair_same_type`,
`same_site_different_type`, `same_word_different_organ`, `simultaneous_distinct_with_distractor`) and 0% in
both granularity families (`granularity_with_laterality_distractor`, `granularity_with_organ_distractor`),
where the target category's own mentions deliberately span two raw anatomy granularities. So category
membership is recoverable from slots alone by construction in six of the eight families; in those families
the discriminating test is whether a method still avoids merging the near-miss distractor category (nonzero
`one_group_per_world` merge rate in every family, `data_card.md`) and whether it gets entity identity right
-- not whether it can recover category membership per se. The two granularity families, plus the entity
axis throughout, carry the tests where getting the *label* right is itself hard. See `data_card.md` for the
full per-family breakdown.

## Release requirements

Identical to v1: In this public release: CC BY 4.0 for data and documentation, MIT for code (the private release candidate
used CC0 for data; the plan of 2026-10-02 replaced it). The private generator manifest, which records the seed
and generator hashes, is withheld. A private freeze manifest records SHA-256 for every v2 file, this contract, and the v1 modules
v2 imports (`schema.py`, `baselines.py`, `worker.py`, `scorer.py`, `runner.py`, and the production
`fact_graph`/`extraction` modules the v1 baselines depend on) -- it never hashes or depends on v1's own
`benchmark_v1/` release or `freeze_manifest.json`. Any change to v2 requires a new version and re-freeze
before outcome evaluation. No external network, LLM, MIMIC input, patient identifier, source report,
evidence span, or restricted derivative is permitted in generation.

## LLM linker on v2

The frozen v1 `llm_linker/` package is reused unmodified (per the freeze that protects it and the live run
in progress against it at the time v2 was built). `evaluation/hidden_identity/v2/llm_v2.py` imports
`evaluation.hidden_identity.llm_linker.config` and rebinds its path constants (`BENCHMARK_INPUTS`,
`BENCHMARK_LABELS`, `RULE_RESULTS`, `OUTPUT_DIR`, `PREDICTIONS_DIR`, `PILOT_DIR`, `STATUS_PATH`, `LOG_PATH`,
`LOCK_PATH`, `RESULTS_PATH`, `LLM_FREEZE_MANIFEST`, `AMENDMENT_DOC`) to v2 locations before dispatching to
`llm_linker.cli.main`, exactly as described in that module's docstring. `llm_linker/worlds.py` also calls
the frozen v1 `schema.validate_inputs` directly (not through a config seam), which hard-codes v1's 6-8
mention bound; since v2 worlds hold 8-14 mentions, `llm_v2.py` additionally replaces the function object
`evaluation.hidden_identity.schema.validate_inputs` with `schema_v2.validate_inputs_v2` at runtime, in this
process only (never writing to `schema.py` on disk, and with no effect on the rule-baseline runner, which
always calls the frozen v1 worker in a fresh subprocess). `llm_linker`'s `pilot` subcommand is
hard-coded to `splits=["train"]`; this is exactly why v2's pilot worlds are stored under `split="train"` in
the first place (see "Families, sizes, seed" above) -- no runtime-filtered-inputs-file indirection is
needed, since the pilot subcommand's hard-coded split selection already reaches exactly the pilot worlds
when `BENCHMARK_INPUTS` points at `benchmark_v2/inputs.json`. `run --splits test` reaches only the 400 main
worlds. Because `llm_linker.scoring`'s contrasts are v1-family-specific, `score_llm_v2.py` scores LLM
predictions with the unmodified v1 scorer and the v2 contrast registry above instead of
`llm_linker.scoring.run_score`.
