# Eval Mutation Prototype: Plan Index

## Purpose

This directory is the implementation handoff for a small research prototype. The prototype asks whether targeted mutations of one AI agent can provide useful construct-validity evidence about that agent's eval suite.

The system under test is intentionally modest: a support-ticket triage agent classifies a request, assigns urgency, searches existing work for genuinely related tickets, and files the result to the correct team. The research object is the measurement process around that agent, not a leaderboard score or a general measure of model intelligence.

## Recommended reading order

1. [01-agent-domain-spec.md](01-agent-domain-spec.md) freezes the workflow, taxonomy, policies, tools, and success boundary.
2. [02-construct-evidence-model.md](02-construct-evidence-model.md) defines the construct, its facets, observable evidence, exclusions, and validity claims.
3. [03-eval-suite-blueprint.md](03-eval-suite-blueprint.md) maps facets into task families, fixtures, evaluators, metamorphic checks, and dataset splits.
4. [04-mutation-experiment.md](04-mutation-experiment.md) defines the lesions, hypotheses, paired experiment, effect matrix, and interpretation rules.
5. [05-technical-architecture.md](05-technical-architecture.md) specifies the Pydantic AI, Pydantic Evals, Ollama, SQLite, configuration, and reporting architecture.
6. [06-implementation-roadmap.md](06-implementation-roadmap.md) breaks implementation into reviewable work packages with acceptance criteria.
7. [07-research-protocol.md](07-research-protocol.md) is the short preregistration template to freeze before examining confirmatory results.

The conceptual background remains in [../agent-eval-analysis-beyond-accuracy.md](../agent-eval-analysis-beyond-accuracy.md).

## Decisions already made

- Use SQLite, not mutable JSON files. It gives deterministic queries, link integrity, transactions, and cheap per-case database copies.
- Keep one primary agent and one turn-level workflow. Do not introduce subagents, a graph framework, RAG, or a web UI.
- Use deterministic database-state and trace evaluators. An LLM judge is unnecessary for the primary outcomes.
- Treat the database after the run as the authoritative outcome. The agent's prose receipt is diagnostic only.
- Keep team assignment, urgency, linking, policy use, and transaction integrity as separate scores. Do not collapse the experiment into one accuracy or mutation number.
- Use Markdown runbooks loaded on demand. They make policy acquisition observable and provide a clean mutation surface.
- Use a frozen development/confirmation split and paired baseline-mutant executions.
- Support Ollama as the default runtime through Pydantic AI's Ollama provider, while keeping model selection configurable.

## What the prototype must establish

The prototype is successful when it can produce all of the following reproducibly:

1. A baseline report with per-facet and per-task-family results, repeat variability, tool traces, and final database state.
2. At least one targeted mutant for each construct facet, plus a broad positive control and a no-op negative control.
3. A lesion-by-task-family matrix showing paired effect estimates and uncertainty.
4. Evidence that at least some targeted lesions affect their predicted task families more than predeclared negative-control families.
5. A written account of equivalent, ineffective, broad, and unexpectedly selective mutants instead of silently forcing them into a mutation score.

This prototype does **not** need to prove a universal psychometric theory, compare a population of models, ship a production ticketing product, or achieve high baseline accuracy. Its purpose is to test whether an interventional validity argument is operationally useful.

## Guardrails for the implementing agent

- Implement the frozen domain before authoring many eval cases.
- Keep fixtures and scorers independent of prompt wording and mutant implementation.
- Never let a case expose its expected team, priority, or link IDs to the agent.
- Reset storage between executions; no case may inherit state from a prior case.
- Record exact model, model digest where available, model settings, prompt/runbook hashes, tool implementation version, fixture hash, dataset version, and retry policy.
- Do not tune on the confirmation set. If confirmation cases change, version the dataset and explain why.
- Prefer simple explicit code over a general mutation framework until two end-to-end mutants work.

