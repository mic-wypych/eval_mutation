# Observed Local Environment

Snapshot checked on 2026-09-12:

- `uv.lock` resolves `pydantic-ai` and `pydantic-evals` to 2.43.0.
- The project requires CPython 3.14.2 or newer. uv already has CPython 3.14.2 installed, although the shell's system `python3` is 3.12.3 and `python` is not on `PATH`. The implementation should use `uv run`.
- Ollama 0.30.7 is installed.
- Locally present model tags are `gemma4:e4b`, `devstral-small-2:24b`, `qwen3.6:27b`, `llama3.2:latest`, and `gpt-oss:20b`.

Begin WP0 compatibility checks with `qwen3.6:27b`, then `gpt-oss:20b` if needed, but treat this order only as a starting point. Tool calling, deferred-capability loading, structured output, latency, and reproducibility remain unverified until the smoke tests run. No additional model download is required for the first check.

Recheck and record all values in the first experiment manifest; local server and model state may change after this snapshot.
