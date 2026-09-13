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

Expected outputs and metadata are loaded by Pydantic Evals but only `inputs` are passed
to the task adapter and agent. Every execution receives a new temporary SQLite database
seeded from the declared fixture.
