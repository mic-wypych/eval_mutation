# Construct and Evidence Model

## 1. Intended score interpretation

> Under the frozen single-turn harness, tool budget, runbooks, ticket-store fixture, and local-model configuration, the eval suite provides evidence about the configured agent's ability to triage synthetic support requests by making policy-consistent routing and urgency decisions, discovering and selecting supported ticket relations, and committing the result safely through tools.

The intended use is research: determine whether targeted interventions produce the predicted pattern of task-level effects. The score is not intended to certify human support agents, compare general intelligence across models, or estimate production incident rates.

## 2. Construct definition

The overall construct is **policy-constrained ticket triage execution**.

It is the ability of one configured agent to convert an inbound request into a correct, traceable, persistent triage action using the information and tools allowed by the harness. “Correct” includes both decision quality and execution. A latent correct answer that is never filed is not successful; a correctly filed ticket reached through leaked labels is also not valid evidence.

## 3. Construct facets

“Construct facet” below means a component of the target ability. It is distinct from a “measurement facet,” which is a source of observed-score variation such as task wording, run, fixture, or grader.

| ID | Construct facet | Definition | Primary observable evidence | Construct-irrelevant threats |
|---|---|---|---|---|
| F1 | Team-routing judgment | Select the policy-authorized owner from request evidence, including boundary and precedence rules | Persisted team; rationale; relevant policy load | Keyword shortcuts, leaked labels, one team dominating cases |
| F2 | Urgency calibration | Map supported impact and immediacy evidence to P0–P3 while ignoring emotional or status cues not in policy | Persisted urgency; cited facts; invariance to urgency decoys | Style/sentiment, implausible impact assumptions |
| F3 | Related-work handling | Retrieve plausible candidates and distinguish true relations from topical resemblance | Search/read trace; link precision and recall; no-link correctness | Fixture search bias, exact-string leakage, empty candidate sets |
| F4 | Policy acquisition and grounded uncertainty | Load needed runbooks, apply non-obvious rules, and use manual triage only when evidence is genuinely insufficient | Loaded capability IDs; decision changes on policy-dependent cases; appropriate abstention | Requiring policy loads on obvious cases, rewarding verbosity |
| F5 | Tool-mediated transaction integrity | Produce one internally consistent, idempotent database change and recover safely from bounded tool errors | Exactly one row; valid foreign keys; receipt/database agreement; audit trace | Tool implementation encoding answers, retry-created duplicates |

These facets are separable for scoring and lesion hypotheses, but the authentic workflow requires their integration. The suite therefore includes both focused cases and integrated cases.

## 4. Evidence chain

| Construct facet | Claim | Evidence collected | Operational task family | Primary evaluator |
|---|---|---|---|---|
| F1 Routing | The agent applies ownership and precedence rules | Correct team across routine and boundary cases; stability under paraphrase | Explicit-route, boundary-route, cross-domain cases | `TeamAssignment`
| F2 Urgency | The agent responds to impact/immediacy rather than tone | Correct P-level; invariance to tone/tier; directional response when impact changes | Urgency-threshold and urgency-decoy cases | `UrgencyAssignment`
| F3 Related work | The agent finds true relations and rejects distractors | Candidate inspection, exact expected link set, precision/recall | True-link, distractor, and no-link cases | `LinkSet` plus trace metrics |
| F4 Policy/uncertainty | The agent consults authoritative rules when necessary and abstains appropriately | Required policy loaded; correct boundary outcome; manual triage on insufficient evidence | Policy-dependent and ambiguity cases | `PolicyUse`, `SafeEscalation`
| F5 Transaction | The agent carries a decision into valid persistent state | Single created ticket, valid values, idempotency, receipt consistency | All cases plus injected recoverable errors | `TransactionIntegrity`

The chain is deliberately redundant: final state supplies product evidence, traces supply response-process evidence, metamorphic relations supply property evidence, and targeted lesions supply interventional evidence.

## 5. Measurement facets and controlled variation

| Measurement facet | Levels in the pilot | Treatment |
|---|---|---|
| Task instance | Multiple requests within every task family | Sampled deliberately; cases are the primary generalization unit |
| Wording variant | Canonical and one semantics-preserving paraphrase on a subset | Crossed for metamorphic checks, not silently pooled |
| Run/sampling | Repeated executions | Report within-case success and paired mutant effects |
| Existing-ticket fixture | Several fixed fixture patterns | Version and stratify; reset per execution |
| Execution order/time block | Randomized order in blocks | Record to diagnose drift and model warming |
| Model build/settings | One frozen primary configuration | Treat any change as a new agent, not another repeat |
| Evaluator version | Deterministic versioned functions | Unit-test against handcrafted states |

Do not call case pass proportion “Rasch item difficulty,” and do not call a case's lesion sensitivity “item discrimination.” This is an N=1 configured-agent measurement study with repeated tasks and occasions.

## 6. Facet score definitions

Each execution produces separate binary or bounded scores:

- `team_correct`: persisted team equals the expected team or permitted team set;
- `urgency_correct`: persisted urgency equals the expected urgency;
- `link_precision` and `link_recall`: computed from persisted relation IDs;
- `link_set_exact`: exact equality for confirmatory pass/fail;
- `policy_behavior_correct`: required policy was available/loaded when stipulated and the policy-dependent behavior is correct;
- `safe_escalation`: manual triage is used exactly when permitted;
- `transaction_valid`: exactly one idempotent ticket exists with valid references;
- `receipt_consistent`: final structured receipt matches persistent state;
- `integrated_success`: conjunctive task-specific criterion declared in case metadata.

An evaluator should skip a non-applicable facet rather than turn it into a vacuous pass. Reports must retain applicable denominators.

## 7. Validity argument

### Content evidence

- Every team, urgency level, boundary rule, relation pattern, and manual-triage condition appears in the blueprint.
- A domain reviewer checks that expected outcomes follow the written runbooks, not intuition.
- Development and confirmation cases share a specification but not templates with superficial answer cues.

### Response-process evidence

- Tool traces show what the agent searched, read, loaded, attempted, and committed.
- The harness detects answer leakage, impossible link IDs, unobserved relation claims, duplicate filing, and receipt/database mismatch.
- A trace is diagnostic; do not require one unique chain of thought or one exact sequence when multiple legitimate processes exist.

### Relations and interventions

- Metamorphic variants test invariance or directional claims.
- Targeted mutants should depress the relevant facet/task block more than negative-control blocks.
- A no-op mutant estimates the experiment's false-kill behavior; a broad destructive mutant verifies that the pipeline can detect obvious degradation but supplies little discriminant evidence.

### Consequences and use

- False routing and false low urgency matter more operationally than verbosity or extra harmless reads, but this research prototype reports them separately instead of creating an unvalidated weighted total.
- The confirmation set is used to test hypotheses, not tune prompts, runbooks, tasks, thresholds, or lesions.

## 8. Rival explanations to investigate

When predicted effects do not appear, consider at least:

- the mutant was behaviorally equivalent or failed to activate;
- the case did not actually require the claimed facet;
- policy knowledge was supplied elsewhere or memorized by the model;
- a shared prerequisite caused broad spillover;
- the scorer is insensitive or incorrectly keyed;
- search fixture ordering leaked the answer;
- local-model tool-call instability overwhelmed the targeted effect;
- the sample is too small for the decision threshold.

The response is diagnosis and revision on development data, not reclassifying every survivor as an eval failure.

## 9. Claims the pilot may and may not support

If the predicted block pattern appears on held-out cases, the pilot may support the claim that the suite is sensitive and partially specific to the represented degradations. It may motivate a broader study.

It may not establish that the construct is a human-like latent trait, that the suite detects all real regressions, that mutations are realistic production faults, or that performance generalizes to other models, domains, prompts, tools, or run policies.

