# Eval datasets

`development.yaml` is the first engineering slice: one authored case for each of the
eight task families. It is development data, not a confirmation set and not yet the
40-case coverage target in the blueprint.

Validate and inspect it without invoking a model:

```bash
uv run python -c "from eval_mutation.evals import load_dataset; print(load_dataset('datasets/development.yaml'))"
```

Run one local case with the default `gemma4:e4b` configuration:

```bash
PYDANTIC_AI_NO_BANNER=1 timeout 30m uv run python -m eval_mutation.evals \
  --case dev-001 \
  --no-progress \
  --output artifacts/dev-001.json
```

Run all development cases sequentially by omitting `--case`. Keep concurrency at one
for a single local Ollama model unless the host has been validated for parallel runs.

When `--output artifacts/dev-001.json` is provided, the runner writes four files:

- `dev-001.json`: the native Pydantic Evals report;
- `dev-001.rows.jsonl`: one reconstructable row per case repeat or task failure;
- `dev-001.summary.json`: assertion rates and mean process scores sliced by task
  family, construct facet, expected team, expected urgency, fixture, and exception;
- `dev-001.manifest.json`: dataset, fixture, runbook, source, evaluator, model,
  framework, Git, host, and artifact provenance.

The runner generates a unique run ID. Pass `--run-id NAME` when an external schedule
needs to assign it. See [the artifact contract](../docs/eval-artifacts.md) for details.

Expected outputs and metadata are loaded by Pydantic Evals but only `inputs` are passed
to the task adapter and agent. Every execution receives a new temporary SQLite database
seeded from the declared fixture.
