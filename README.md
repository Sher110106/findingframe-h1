# H1: a hidden-identity linker benchmark

H1 tests one narrow thing. Given structured findings from a patient's timeline of reports, can a system
group them correctly in two ways?

- **Category**: same finding type, organ-level site and side.
- **Entity**: the same individual lesion, followed over time.

The data is synthetic. Each world is a list of mention records. Each record carries structured frame slots
(`finding_type`, `anatomy`, `laterality`, `assertion`, `measurement`, `temporal_change`, `finding_surface`,
`evidence_text`, report and timeline position) and sometimes a `descriptor`. A system returns a category
partition and an entity partition for every world.

## What H1 does not test

- It is **not** a raw-report benchmark. The frames are given (oracle frames). No system reads report text
  to extract them.
- It is **not** clinical validation. All worlds are authored, and no clinician labelled anything.
- It holds no MIMIC text and no patient identifiers.
- It does not rank the FindingFrame linker. Rows for that linker are labelled
  "author reference baseline (FindingFrame linker, unranked)".

## Scoring

- **Category B-cubed F1** and **Entity B-cubed F1** are the two headline numbers. We never combine them.
- We also report split and merge pair rates, coverage, MUC and CEAF-E.
- A missing, timed-out or unparsable answer is not a zero. Its mentions count as unresolved singletons, and
  the world stays in the denominator. This is the scorer's rule for v2.
- Overall rows are equal-world means with a world bootstrap (seed 42, 10,000 draws). Family rows use the
  same bootstrap inside one family. Paired contrasts resample worlds within each family and average the
  families equally.

`h1bench/scorer.py` is a byte-for-byte copy of the scorer used in the paper.

## Quickstart

```bash
git clone https://github.com/Sher110106/findingframe-h1 && cd findingframe-h1
python -m venv .venv && source .venv/bin/activate
pip install -e ".[openai,test]"
pytest -q
h1bench smoke
h1bench baselines --split dev

export OPENAI_API_KEY=...
h1bench run --split dev --base-url https://api.openai.com/v1 --model gpt-4o-mini
h1bench score --split dev predictions_dev_gpt-4o-mini.jsonl

h1bench run --split test --base-url https://api.openai.com/v1 --model gpt-4o-mini
h1bench make-submission predictions_test_gpt-4o-mini.jsonl --model "gpt-4o-mini"
```

`smoke` runs offline in a few seconds. Any OpenAI-compatible endpoint works. Pick the key variable with
`--api-key-env`. `run` writes `predictions_<split>_<model>.jsonl` unless you pass `--out`. See
[SUBMITTING.md](SUBMITTING.md) for what to do with the test submission.

`run` is resumable. Re-run the same command to finish an interrupted file. Add `--retry-failed` to retry
worlds that failed. `h1bench score --split test` refuses to run, because no test labels are shipped.

## Data

| path | content | labels |
|---|---|---|
| `data/v2/test_inputs.json` | 400 v2 test worlds: `world_id` and `mentions` only | withheld |
| `data/dev/v2_pilot/` | 24 v2 pilot worlds (8 families, 3 each) | yes |
| `data/dev/v1/` | 900 v1 train and dev worlds | yes |

Only v1 train and dev worlds ship. There is no v1 test split here.

**v1 development data has a known flaw.** Seven of its nine families hold exactly one gold category per world,
and every v1 test world held one. The other two, `laterality_change` and `report_order_permutations`, hold two. A system that puts each world in one group scores Category F1 1.000 there.
v1 category scores measure over-splitting only. v2 fixes this: each world holds two or three categories with
near-miss distractors. Use v2 for any claim about category linking. See [DATA_CARD.md](DATA_CARD.md).

## Read this first: v2 is a diagnostic, not a leaderboard

- Simple rules solve the Category axis. The strict-laterality ablation scores Category F1 1.000, and so does a
  rule written by hand from the public contract.
- Entity is the axis that separates systems.
- That hand-written rule scored Entity F1 0.955 on the private test labels. This is above every published
  row (the best is 0.927, the strict-laterality ablation). We do not ship the rule.
- Treat v2 as a diagnostic of linking behaviour, not a leaderboard.
- Raw-text v3 is planned to remove this ceiling.

## Results (v2 test, 400 worlds)

Rows are in no rank order. Full tables, per-family numbers and contrasts are in
[results/v2_test_results.md](results/v2_test_results.md) and
[results/v2_test_results.json](results/v2_test_results.json).

| system | answered | Category F1 [95% CI] | Entity F1 [95% CI] | cat split | cat merge | ent split | ent merge |
|---|---|---|---|---|---|---|---|
| DeepSeek v4.1 flash | 400/400 | 0.925 [0.911, 0.938] | 0.888 [0.876, 0.900] | 0.142 | 0.000 | 0.170 | 0.088 |
| GLM 5.3 flash | 342/400 | 0.850 [0.825, 0.873] | 0.817 [0.794, 0.839] | 0.245 | 0.000 | 0.254 | 0.089 |
| one_group_per_world (public) | 400/400 | 0.676 [0.669, 0.682] | 0.599 [0.590, 0.608] | 0.000 | 0.539 | 0.000 | 0.628 |
| one_group_per_mention (public) | 400/400 | 0.344 [0.340, 0.348] | 0.392 [0.385, 0.398] | 1.000 | 0.000 | 1.000 | 0.000 |
| raw_surface_equality (public) | 400/400 | 0.603 [0.594, 0.612] | 0.575 [0.567, 0.584] | 0.547 | 0.437 | 0.553 | 0.568 |
| exact_normalized_key (author reference) | 400/400 | 0.920 [0.906, 0.933] | 0.847 [0.835, 0.860] | 0.151 | 0.000 | 0.151 | 0.176 |
| current_compatibility_linker (author reference) | 400/400 | 0.947 [0.933, 0.960] | 0.874 [0.860, 0.888] | 0.093 | 0.000 | 0.093 | 0.176 |

"Author reference" means the FindingFrame linker, unranked. Its code is not in this repository, so these
rows are context only. The results file also lists the ablations (strict laterality, no anatomy hierarchy,
raw anatomy, descriptor comparator, order variants).

GLM answered 342 of 400 worlds. For the other 58 it spent its whole token budget on reasoning in all three
tries. Those worlds score as unresolved singletons and stay in the denominator. This earns partial credit, not
zero: mean category F1 on the 58 failed worlds is 0.326. GLM's numbers therefore mix quality
with failure to answer.

Both LLMs ran at temperature 0, one run per world (GLM had up to three attempts per world), with the prompt in `h1bench/prompts/`. The runner in this
repository reproduces that prompt exactly: the per-world prompt hash matches the paper's records on 400 of
400 DeepSeek test worlds.

## How to submit

Open a pull request that adds `submissions/<team>-<model>/submission.json`. The maintainer scores it with
the private labels and posts aggregate and per-family scores only. See [SUBMITTING.md](SUBMITTING.md).

## What is not here

Test labels for v1 and v2, per-world scores and predictions, the generator and its seeds, and the
FindingFrame production code (`fact_graph/`, `extraction/`). Without the generator, nobody can regenerate
the test labels. `MANIFEST.json` lists each file with its SHA-256 and its source path in the private
research repository. `CHECKSUMS.sha256` lists the same hashes for `sha256sum -c`.

## Citation

See [CITATION.cff](CITATION.cff). The author list is pending.

## License

Code: MIT ([LICENSE](LICENSE)). Data and documentation: CC BY 4.0 ([LICENSE-DATA](LICENSE-DATA)).
