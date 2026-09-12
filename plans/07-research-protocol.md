# Research Protocol / Preregistration Template

Copy this file to a dated, versioned protocol and replace every bracketed field before confirmatory runs.

## 1. Research question

Can targeted lesions of the frozen ticket-triage agent produce task-family and facet-score effects that match the predeclared construct map, while sparing predeclared negative-control families?

## 2. Frozen system under test

| Item | Value |
|---|---|
| Git commit and dirty state | [fill] |
| Base prompt hash | [fill] |
| Runbook hashes | [fill] |
| Tool/repository version | [fill] |
| Pydantic AI/Evals versions | [fill] |
| Ollama version | [fill] |
| Model tag and digest | [fill] |
| Output mode | [fill] |
| Temperature/seed/settings | [fill] |
| Request/tool/token/time budgets | [fill] |
| Transport retry policy | [fill] |

## 3. Frozen measurement artifacts

| Item | Value |
|---|---|
| Confirmation dataset path/hash | [fill] |
| Fixture paths/hashes | [fill] |
| Evaluator version/hash | [fill] |
| Analysis version/hash | [fill] |
| Confirmation case count | [fill] |
| Repeats per configuration/case | [fill] |

## 4. Included mutants

For each included mutant, record:

| Mutant ID | Version/hash | Construct target | Severity | Activation check | Realism rationale |
|---|---|---|---|---|---|
| [fill] | [fill] | [fill] | [fill] | [fill] | [fill] |

List screening exclusions and reasons here: [fill].

## 5. Confirmatory hypotheses

Use exact case IDs and exact evaluator outcomes, not only family names.

| Hypothesis ID | Mutant | Target cases/facets | Negative-control cases/facets | Expected direction | Minimum meaningful effect |
|---|---|---|---|---|---|
| [fill] | [fill] | [fill] | [fill] | Baseline minus mutant greater than zero | [fill] |

## 6. Execution schedule

- Pairing unit: case × repeat × fixture × honored seed.
- Randomization method and seed: [fill].
- Blocking variable, such as time window: [fill].
- Concurrency: [fill].
- Warm-up policy for local model: [fill].
- Infrastructure-failure rerun policy: [fill].
- Semantic failure reruns: none unless [predeclared exception].
- Early stopping: [none, or exact rule].

## 7. Primary and secondary outcomes

Primary outcomes: [list exact facet scores and target/control contrasts].

Secondary outcomes: integrated success, duration, tool calls, policy loads, link precision/recall, model usage, and metamorphic violation rates.

The main display is the lesion × task-family/facet matrix. Aggregate mutation counts are secondary.

## 8. Statistical model and thresholds

- Estimator/model: [hierarchical binary model or case-clustered bootstrap, exact specification].
- Interval/posterior summary: [fill].
- Target-detection rule: [fill; planned default is P(degradation > 0.15) >= 0.90].
- Localization rule: [fill; planned default is P(target minus control > 0.10) >= 0.90].
- Broad-effect rule: [fill].
- Multiple-hypothesis handling or rationale for descriptive pilot treatment: [fill].
- Sensitivity analyses: [nearby thresholds, inclusion choices, model variants].

## 9. Exclusions and missing data

Predeclare treatment of:

- transport/model-server failures;
- tool timeouts;
- invalid structured output;
- violated database invariants;
- unverified mutant activation;
- equivalent/ineffective mutants;
- partial experiment blocks;
- contaminated or ambiguous cases discovered after freezing.

Exact rules: [fill].

## 10. Trace review

- Reviewer blinding: [fill].
- Mandatory review set: all target survivors, large control effects, invalid runs, and [percentage] random expected outcomes.
- Reason-code taxonomy version: [fill].
- Adjudication process: [fill].

## 11. Decision and claim boundary

The study will be considered supportive of the prototype idea if: [fill exact required number/pattern of localized effects and no-op behavior].

It will be considered inconclusive if: [fill].

It will count against the current operationalization if: [fill, including broad/non-specific response or unstable no-op effects].

Regardless of outcome, claims remain limited to the frozen configured agent, represented mutations, tasks, and execution envelope.

## 12. Deviations

Record every post-freeze deviation with timestamp, reason, affected runs, and whether analysis was conducted before the decision: [fill].
