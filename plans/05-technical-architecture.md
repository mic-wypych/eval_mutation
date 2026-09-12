# Technical Architecture

## 1. Minimal component map

| Component | Responsibility |
|---|---|
| Agent factory | Build the intact or named-mutant Pydantic AI agent from explicit configuration |
| Model factory | Resolve Ollama/local or optional remote provider without changing agent logic |
| Runbook loader | Parse Markdown runbooks into stable deferred capabilities |
| Ticket repository | Provide typed SQLite reads/writes and enforce integrity/idempotency |
| Tool adapter | Expose repository operations to the agent and emit audit events |
| Eval task adapter | Create isolated case state, run the agent, and return output plus artifacts |
| Dataset loader | Load typed Pydantic Evals YAML cases and metadata |
| Evaluators | Score final state, output, and traces deterministically |
| Mutation registry | Apply one explicit reversible intervention by ID |
| Experiment runner | Run repeated, paired baseline/mutant experiments and write manifests/results |
| Analyzer | Build slice tables, effect estimates, lesion matrix, and Markdown/CSV reports |

Do not introduce a service layer or web application. A command-line entry point and library modules are sufficient.

## 2. Proposed repository layout

The implementing agent should create this shape, adjusting names only for a clear reason:

| Path | Contents |
|---|---|
| `src/eval_mutation/domain/` | Pydantic models, enums, policy rule IDs |
| `src/eval_mutation/agent/` | Agent/model factories, base instructions, output model |
| `src/eval_mutation/agent/runbooks/` | Routing, urgency, and relation Markdown capabilities |
| `src/eval_mutation/storage/` | SQLite schema, repository, fixture cloning |
| `src/eval_mutation/tools/` | Pydantic AI function-tool adapters |
| `src/eval_mutation/evals/` | Task adapter, dataset loading, evaluators, report evaluators |
| `src/eval_mutation/mutations/` | Registry, configuration models, prompt/tool mutations |
| `src/eval_mutation/experiments/` | Run orchestration, manifests, pairing, analysis |
| `datasets/` | Development, confirmation, and schema YAML/JSON files |
| `fixtures/` | Versioned ticket-store seeds |
| `tests/` | Unit, contract, integration, and small deterministic end-to-end tests |
| `artifacts/` | Git-ignored generated manifests, long-form results, reports, and matrices |
| `plans/` | This implementation and research plan |

## 3. Pydantic AI design

- Build one `Agent` with typed dependencies holding the case-scoped repository, frozen clock, run ID, and trace/audit collector.
- Expose the five tools in the domain spec as typed function tools.
- Use a typed triage receipt as the output model, but score the repository state as authoritative.
- Represent the three policy files as Pydantic AI `Capability` objects with stable IDs and deferred loading.
- Keep the base system instructions short: role, workflow, need to use tools, exactly-once filing, runbook authority, and safe uncertainty behavior.
- Put boundary rules in runbooks so that on-demand policy use and policy mutations are observable.
- Set explicit usage limits and model-request/tool-call budgets.
- Instrument tool calls and capability loads independently of optional hosted observability.

Current Pydantic AI documentation supports deferred capabilities that reveal instructions/tools after a `load_capability` call and can wrap Markdown policy files. The implementation should pin the framework version and add a compatibility test because this surface may evolve.

## 4. Ollama and model portability

Use the Pydantic AI Ollama model/provider path, with local base URL `http://localhost:11434/v1`. Make model name, base URL, temperature, timeout, seed, and context limit configuration fields recorded in every manifest.

Selection criteria for the default local model:

- reliable function/tool calling;
- support for the chosen structured-output strategy;
- enough context for three short runbooks and returned ticket candidates;
- acceptable latency for repeated runs;
- a fixed tag/digest that can be recorded.

Start compatibility testing with one modest tool-capable model available in the user's Ollama installation; do not hard-code an unverified model download into the project. The first smoke test should verify multi-step behavior: load a capability, search, read, file, and return a valid receipt.

Pydantic AI currently offers a dedicated `OllamaModel`. Self-hosted recent Ollama versions can enforce native JSON-schema output, but default tool-based structured output is the safer initial cross-provider choice. Treat changing output mode as a harness change and do not pool those runs.

## 5. SQLite state model

### `tickets`

- primary key ticket ID;
- unique nullable inbound `request_id` for idempotency;
- title/body/customer/channel/submitted timestamp;
- team and urgency enums;
- status and created timestamp;
- summary and rationale;
- fixture/new-row marker.

### `ticket_links`

- source ticket ID;
- target ticket ID;
- relation type, initially only `related`;
- created timestamp;
- unique source/target pair;
- foreign-key constraints and no self-link.

### `audit_events`

- run ID and ordered sequence;
- tool/capability/action name;
- normalized arguments and result summary;
- success/error code;
- mutant activation marker if applicable;
- timestamp from the frozen case clock or monotonic sequence.

Use one template fixture database per fixture ID and copy it to a temporary path for every execution. Do not share a writable connection across concurrent case runs. Validate that only allowed tables/rows changed before scoring.

## 6. Pydantic Evals integration

- Model cases as typed `Dataset[Input, Output, Metadata]` records.
- Keep shared deterministic evaluators at dataset level and family-specific evaluators in case metadata or case-level configuration.
- Use YAML serialization for reviewable datasets and generated JSON Schema for validation/autocomplete.
- Use the current multi-run `repeat` mechanism for baseline exploration where it preserves case isolation; otherwise expand repeats explicitly in the experiment runner.
- Use report-level evaluators or a separate analysis layer for confusion matrices and slice summaries.
- Export raw per-run results before aggregation.

The experiment runner will need behavior beyond a single dataset evaluation: paired ordering, per-configuration manifests, mutation activation, and baseline-mutant joins. Keep this orchestration outside evaluator logic.

## 7. Run artifact contract

Every experiment writes an immutable manifest and long-form results.

### Manifest

- experiment and preregistration ID;
- timestamp/time block;
- git commit and dirty-state flag;
- dataset/split and hashes;
- fixture/runbook/base-prompt hashes;
- intact or mutant ID/version;
- mutation activation contract;
- model provider/name/digest/settings;
- framework and package versions;
- retry, concurrency, timeout, and budget policies;
- host information relevant to local inference;
- randomization schedule and seeds.

### Per-run row

- experiment, case, metamorphic group, repeat, and pair IDs;
- task family/facet tags;
- configuration and mutant ID;
- all evaluator results with applicability;
- model/tool timing and usage;
- exception category;
- artifact paths for normalized trace and final database snapshot hash.

Prefer JSON Lines or Parquet for raw output and CSV plus Markdown for human-facing summaries. Do not rely only on console-rendered Pydantic Evals reports.

## 8. Mutation mechanism

Use a registry of named mutation specifications rather than scattered environment conditionals. Each specification declares:

- target component and version;
- transform or alternate implementation;
- activation check;
- expected task/facet map;
- severity;
- rationale and realism note.

Agent construction accepts zero or one mutation ID for the MVP. This prevents accidental compound mutants and makes manifests unambiguous. Only later consider factorial combinations.

## 9. Testing strategy

### Unit tests

- domain enum/schema validation;
- repository queries, links, idempotency, and transactions;
- runbook loading and stable capability IDs;
- every evaluator on positive, negative, skipped, and malformed states;
- each mutant's transformation and activation marker;
- report effect calculations on synthetic data.

### Contract tests

- tool schemas exposed to the model match repository behavior;
- case isolation under concurrency;
- baseline and mutant share unchanged dataset/evaluators;
- manifest contains all provenance fields;
- output/database disagreement is detected.

### Model-free agent tests

Use Pydantic AI's test/function model facilities for deterministic tool-flow tests. These tests verify orchestration only; they are not evidence about the local model's capability.

### Local-model smoke tests

- one routine route;
- one policy load plus boundary decision;
- one search/read/link/file workflow;
- one manual-triage case;
- one activated prompt mutant and one tool mutant.

## 10. Dependency and version policy

- Pin exact Pydantic AI/Evals versions after the first working integration instead of leaving only a lower bound.
- Add Pydantic Evals explicitly if the installed meta-package does not make the dependency contract clear.
- Keep analysis dependencies optional and minimal until the data format is stable.
- Record the Ollama server version and model digest outside Python dependency metadata.
- Re-run contract tests before accepting dependency upgrades; framework upgrades define a new harness version for research comparisons.

## 11. Current primary references

- Pydantic AI Ollama provider: <https://pydantic.dev/docs/ai/models/ollama/>
- Pydantic AI deferred capabilities: <https://pydantic.dev/docs/ai/capabilities/on-demand/>
- Pydantic Evals core concepts: <https://pydantic.dev/docs/ai/evals/getting-started/core-concepts/>
- Pydantic Evals multi-run evaluation: <https://pydantic.dev/docs/ai/evals/how-to/multi-run/>
- Pydantic Evals dataset serialization: <https://ai.pydantic.dev/evals/how-to/dataset-serialization/>
- Pydantic AI testing: <https://pydantic.dev/docs/ai/guides/testing/>

