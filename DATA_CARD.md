# Data card: H1 hidden-identity benchmark

## Summary

Synthetic worlds for testing category and entity linking over a patient timeline. A v2 world has 8 to 14
mentions spread over 3 to 5 reports (v1: 6 to 8 mentions). Mentions carry structured frame slots and authored evidence text. The
text comes from templates written for this benchmark.

No MIMIC text, no patient identifiers, no clinician labels. Gold categories and entities come from the
latent world that rendered the mentions. They are an engineering reference, not clinical truth.

## Versions

| version | role | worlds | categories per world |
|---|---|---|---|
| v2 test | scoring, labels withheld | 400 (8 families, 50 each) | 2 to 3 |
| v2 pilot | development, labels shipped | 24 (8 `_pilot` families, 3 each) | 2 to 3 |
| v1 train and dev | development, labels shipped | 900 (9 families, 100 each) | 1 to 2 |
| v1 test | withheld entirely | 800 | 1 |

### The v1 flaw

Every v1 test world holds one gold category. In v1 train and dev, seven of nine families hold one, and only
`laterality_change` and `report_order_permutations` hold two. Putting every mention of a world in one group
scores Category F1 1.000 in a one-category family, and a category merge error cannot occur there. v1
category scores therefore measure over-splitting only. v2 gives each world a target category and one or two
near-miss distractors that share wording, organ, side or finding type with it.

## v2 families

`granularity_with_laterality_distractor`, `granularity_with_organ_distractor`, `laterality_pair_same_type`,
`same_word_different_organ`, `same_site_different_type`, `simultaneous_distinct_with_distractor`,
`descriptor_pair_with_distractor`, `episode_reuse_with_distractor`.

In six of the eight families, grouping by the raw `(finding_type, anatomy, laterality)` tuple recovers the
gold category partition exactly. In both granularity families it never does, because the target category
spans two anatomy granularities (for example lobe and organ). See the contract for the full design.

## Fields

Per world: `world_id` (opaque hash). Development worlds also carry `scenario_family` and `split`.

Per mention: `mention_id` (opaque hash), `frame`, and an optional `descriptor`.

`frame` holds exactly: `source_report_id`, `source_timeline_index`, `frame_index`, `finding_type`, `anatomy`,
`laterality`, `assertion`, `measurement`, `temporal_change`, `finding_surface`, `evidence_text`.

The test file has no `scenario_family` and no `split`. The LLM runs in the paper did not receive them
either. The paper's runner also dropped a `probe` field present in some v1 records; the development files
here omit it.

In v2, mention order within a world follows `(source_timeline_index, frame_index)`. The generator shuffles
mentions within each report, and we found no link between order and labels beyond the timeline. Worlds in the test
file are sorted by `world_id`, a hash, so file position does not reveal the family.

`world_id` is derived from generation parameters that include the family name, so someone who guesses those
parameters can recover each test world's family. The family does not reveal labels, and the models in the paper
never saw it. We kept the IDs unchanged because they appear inside the prompts the reported models received.

## Checks run before release

- The public test inputs equal what the LLM runs saw. The per-world prompt hash of every DeepSeek test
  record matches the hash recomputed from `data/v2/test_inputs.json` (400 of 400).
- The scorer in `h1bench/scorer.py` is byte-identical to the paper's. A maintainer scorer built on the
  private labels reproduces the published aggregates for DeepSeek and for the public baselines, to the
  last digit.
- A scan of every file for label keys, seeds, absolute paths, secrets and patient-identifier-like numbers.

## Withheld

Test labels (v1 and v2), per-world scores, per-world predictions, the generator, seeds and generation
configs, and the FindingFrame production modules. Identifiers (`world_id`, `mention_id`, `source_report_id`) are
hashes. They contain no label.

## Known limits

- Oracle frames. Frame errors are not tested.
- Authored text from templates. Real report language is more varied.
- The gold reference is engineered. Some worlds may not be resolvable from the inputs alone, and the
  benchmark does not establish which.
- v2 has 50 worlds per family. Per-family intervals are wide for entity scores.
- Two LLMs have run on it, each once, so the results are a starting point and not a survey.

## License

CC BY 4.0 for data and documentation. MIT for code.
