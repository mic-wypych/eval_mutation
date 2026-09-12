# Implementation Roadmap

## Working method

Implement in vertical slices. The first meaningful milestone is one case that loads a policy, reads fixture state, files a ticket, is deterministically scored, and can be rerun under one activated mutant. Generalization comes afterward.

Each work package below should be a small reviewable change. Do not begin confirmation runs until the research protocol is frozen.

## WP0: Resolve environment and freeze interfaces

### Tasks

- Confirm the Python version is actually available and supported by the chosen dependency versions.
- Inspect installed Ollama version and locally available tool-capable model tags/digests.
- Select one primary local model after a tool-calling smoke test.
- Pin Pydantic AI and Pydantic Evals versions.
- Create configuration and provenance conventions.
- Turn the domain tables in the plan into versioned decision records.

### Acceptance criteria

- A documented local command can reach Ollama.
- The chosen model completes one typed function call and one structured result.
- Exact framework, server, and model versions are recorded.
- Any deviation from the domain spec has a written rationale before cases are authored.

## WP1: Domain and isolated storage

### Tasks

- Implement typed request, ticket, receipt, expected-state, metadata, team, urgency, and error models.
- Implement SQLite schema, repository, fixture seed format, cloning, and teardown.
- Enforce foreign keys, no self-link, unique links, and `request_id` idempotency.
- Add audit events and deterministic/frozen timestamps.
- Seed two small fixtures: one no-link fixture and one true-link-plus-distractors fixture.

### Acceptance criteria

- Repository unit tests cover all reads/writes and constraint failures.
- Two concurrent cases cannot observe or mutate each other's state.
- Repeating a filing call with one request ID creates at most one ticket.
- A fixture hash and final database snapshot hash can be produced.

## WP2: Intact agent vertical slice

### Tasks

- Write the minimal base instructions.
- Write and parse the three Markdown runbooks with stable policy rule IDs.
- Register deferred capabilities.
- Implement typed read/search/list/file/link tools.
- Implement the structured receipt and one agent factory.
- Add tool budgets, timeouts, trace capture, and normalized errors.

### Acceptance criteria

- The local model completes routine, policy-boundary, link, and manual-triage smoke cases.
- Exactly-once filing is enforced even if the model retries.
- Capability loads and every tool call appear in ordered trace artifacts.
- Final receipt/database inconsistency is observable.

## WP3: Eval harness and deterministic scoring

### Tasks

- Implement typed Pydantic Evals case models and YAML/schema loading.
- Implement isolated case setup/teardown in the task adapter.
- Implement every deterministic evaluator in the blueprint.
- Add report slicing by task family, facet, team, urgency, fixture, and exception type.
- Export raw long-form results and a run manifest.
- Write initial development cases: one or two per task family.

### Acceptance criteria

- Evaluators pass exhaustive handcrafted-state tests.
- Re-running a case begins from the same fixture hash.
- Applicable and skipped denominators are correct.
- Raw rows can reconstruct every summary metric.
- No expected answer fields are visible in the agent input or tools.

## WP4: First end-to-end mutant

### Tasks

- Implement the mutation registry and zero-or-one-mutant configuration.
- Implement M2 urgency-policy mutation and its activation check.
- Run paired baseline/M2 executions on one target and one negative-control development case.
- Produce the first two-row effect comparison and trace-review notes.

### Acceptance criteria

- Baseline and mutant differ only in the manifested mutation.
- The mutated text is hashed and archived.
- Activation is proven in the trace or manifest.
- Dataset and evaluator hashes match across the pair.
- The report does not call a non-activated mutation a survivor.

## WP5: Development suite and baseline reliability

### Tasks

- Complete 24 development cases and required fixtures from the coverage grid.
- Add valid metamorphic variants.
- Conduct independent answer-key review against rule IDs.
- Run at least three baseline repeats per case and five per sentinel candidate.
- Diagnose unstable cases and select the 12-case sentinel set.
- Run simple shortcut/leakage audits.

### Acceptance criteria

- All development coverage targets are met.
- All retained expected outputs are policy-derivable.
- Instability is reported by case rather than hidden in an average.
- Sentinel selection rationale emphasizes coverage, stability, and cost.
- Development dataset version is frozen for mutation engineering.

## WP6: Mutant catalog and screening

### Tasks

- Implement M1–M8 with unit tests and activation probes.
- Write exact prediction/control mappings at case and scored-facet level.
- Run three paired repeats on the sentinel set.
- Classify equivalent/ineffective, broad, and targeted candidate mutants.
- Refine only on development data.

### Acceptance criteria

- Every mutant has a causal rationale, realism note, version, severity, and activation evidence.
- No mutant changes dataset/evaluator hashes.
- No-op false detections and broad-control detection are visible.
- Screening produces a draft lesion matrix and a list of mutants eligible for confirmation.

## WP7: Confirmation set and preregistration

### Tasks

- Author 16 fresh confirmation cases from the existing blueprint.
- Review keys independently and run only deterministic fixture/evaluator checks.
- Finalize target/control case IDs, effect estimands, thresholds, exclusions, run count, and stopping behavior.
- Fill and commit the research protocol in `07-research-protocol.md` or a versioned copy.
- Hash/freeze confirmation dataset, runbooks, agent, evaluators, fixtures, and analysis implementation.

### Acceptance criteria

- Confirmation content has not been used for prompt, model, case, or mutant tuning.
- All hypothesis cells have an exact case/facet interpretation.
- Exclusion and equivalent-mutant rules are executable or independently reviewable.
- The preregistration identifies any deviations from this planning document.

## WP8: Confirmatory execution and analysis

### Tasks

- Generate a randomized, blocked paired-run schedule.
- Run baseline and eligible mutants five times on target and control cases.
- Monitor only infrastructure/activation failures; do not inspect semantic outcomes mid-run to tune the system.
- Fit the predeclared model or clustered bootstrap.
- Generate lesion matrix, target/control contrasts, reliability slices, and trace-review sample.
- Conduct and record blinded trace review where practical.

### Acceptance criteria

- All included runs match frozen hashes and versions.
- Infrastructure reruns follow the predeclared policy.
- Matrix cells include estimates, uncertainty, counts, and activation rates.
- Unexpected effects receive reason codes.
- Raw data, manifest, analysis inputs, and report are reproducible from one documented workflow.

## WP9: Research conclusion

### Tasks

- Write what the experiment supports, contradicts, and leaves unresolved.
- Separate suite sensitivity from specificity and mutant realism.
- Document task-map, runbook, scorer, and mutation revisions suggested by the findings.
- Decide whether the next study needs more cases, another local model, real incident-derived mutations, or a general mutation API.

### Acceptance criteria

- Conclusion does not rely on aggregate baseline accuracy or mutation score alone.
- Equivalent mutants and no-op results remain visible.
- Claims are bounded to the frozen agent and protocol.
- Next steps are driven by observed uncertainty and rival explanations.

## Suggested pull-request sequence

1. Domain models and SQLite repository.
2. Agent, runbooks, tools, and local-model smoke tests.
3. Typed dataset and deterministic evaluators.
4. M2 vertical slice and paired artifact format.
5. Development suite and reliability report.
6. Full mutant catalog and sentinel screen.
7. Confirmation dataset plus frozen protocol.
8. Confirmatory runner, analysis, and report.

## Stop conditions

Pause expansion and diagnose before proceeding if:

- the local model cannot perform the basic multi-tool workflow reliably enough to distinguish semantic from protocol failures;
- tool or database state leaks expected answers;
- baseline outcomes are dominated by infrastructure errors;
- the no-op mutant is frequently detected;
- mutant activation cannot be proven; or
- confirmation cases require policy changes to obtain unambiguous keys.

