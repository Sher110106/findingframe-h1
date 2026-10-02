# Submitting to the H1 v2 test set

The test labels stay private. A maintainer scores each submission and posts the result.

## Steps

1. Run your system on the test inputs. With the bundled runner:

   ```bash
   h1bench run --split test --base-url <endpoint> --model <model> --out test.jsonl
   ```

   Any other system works if it writes one record per world in the same format (below).
2. Check that the output is complete and write the submission file:

   ```bash
   h1bench make-submission test.jsonl --model "<model name and version>"
   ```

   This validates the file against `data/v2/test_inputs.json` and writes `submission.json` with the model
   name, the date, a prompt hash and the checksum of the test inputs.
3. Open a pull request that adds one file: `submissions/<team>-<model>/submission.json`.
4. The maintainer validates the file, scores it with the frozen private labels, and comments with the
   aggregate and per-family scores. Nothing else is posted. The maintainer does not publish per-world scores
   or predictions, and asks that you do not either.

## Rules

- One scored submission per model version per 7 days. This limits probing of the test set.
- Do not tune on the test inputs. Use the development data (`data/dev/`), which ships with labels.
- A world you do not answer, or answer in a form that does not parse, scores as unresolved singletons and
  stays in the denominator. Missing worlds are never dropped. Use `--allow-missing` only to submit a partial
  run on purpose.
- Say in the pull request if you used a prompt other than the one in `h1bench/prompts/`. `make-submission`
  records how many worlds match the reference prompt.
- Category F1 and Entity F1 are two scores. The maintainer does not combine them, and the project does not
  publish a single ranking number.

## Record format

`h1bench run` writes JSONL, one record per world:

```json
{"world_id": "w_...", "status": "ok",
 "assignments": {"category": {"m_...": "cluster_000001"}, "entity": {"m_...": "cluster_000001"}}}
```

- `status` is `ok`, `failed_api` or `failed_parse`. A failed record has `"assignments": null`.
- Each partition maps every `mention_id` of the world to a cluster label (a string). `null` marks a
  mention as unresolved.
- Mentions with the same label in a partition are in the same group of that partition.

`submission.json` holds the same information keyed by `world_id`, plus the metadata fields.
