# Eval Suite Blueprint

## 1. Design principle

Author cases from the construct map and runbooks. Do not start from convenient examples and attach facet labels afterward. Every case must state:

- the rule it instantiates;
- the facet(s) it is intended to elicit;
- the required and forbidden evidence;
- its expected persistent state;
- the applicable evaluators;
- its predicted sensitive lesions and negative-control lesions; and
- any metamorphic variants.

## 2. Task families

| ID | Task family | Main facets | Case pattern | Required evidence | Negative-control role |
|---|---|---|---|---|---|
| T1 | Routine explicit routing | F1, F5 | One clear team, normal urgency, no relations | Correct team and one valid filing | Should survive linking lesions |
| T2 | Routing boundary/precedence | F1, F4, F5 | SSO plus compromise, billing UI defect, promised-vs-requested behavior | Relevant routing policy and precedence outcome | Should mostly survive urgency-only lesion |
| T3 | Urgency thresholds | F2, F4, F5 | Facts near P0/P1 or P1/P2 boundary | Correct level grounded in impact/immediacy | Team assignment should survive urgency lesion |
| T4 | Urgency decoys | F2, F5 | “URGENT,” angry tone, VIP tier, or repetition without severe impact | Invariance to non-policy cue | Control for routing and relation lesions |
| T5 | True related ticket | F3, F5 | One or more candidates share incident/root cause | Search/read as needed and exact true link set | Team/urgency should survive search degradation where explicit |
| T6 | Relation distractors/no-link | F3, F5 | Same keywords/team but different symptom/customer/incident | No unsupported links; useful candidate inspection | Detect over-linking and broad “link everything” mutants |
| T7 | Policy-dependent ambiguity | F4, F1 or F2, F5 | Missing key ownership facts or truly conflicting cues | Correct `manual_triage` or policy-specific resolution | Should survive linking lesions |
| T8 | Integrated triage | F1–F5 | Boundary routing plus urgency plus mixed relation candidates | Correct full state and coherent trace | Authentic-workflow block; not a clean negative control |

## 3. Coverage targets

Build a lean pilot of 40 authored base cases:

- 24 development cases: three per task family;
- 16 frozen confirmation cases: two per task family;
- a 12-case sentinel subset selected from development cases, with at least one from every family and extra representation of T2, T3, T5, and T6.

Within the full 40 cases, enforce these minimums:

- every non-manual team is the correct destination at least five times;
- every urgency level appears at least six times;
- at least eight cases have true relations and eight have plausible distractors/no valid link;
- at least six cases require a non-obvious runbook rule;
- at least four cases correctly require manual triage;
- no team or urgency label can be inferred from case naming or fixture IDs.

Forty cases are enough to test the pipeline and expose gross block structure, not enough for strong general population claims. Add cases only after the first lesion experiment shows where information is missing.

## 4. Case record specification

Each Pydantic Evals case should carry typed input, expected output, and metadata.

### Input

- inbound request fields from the domain spec;
- fixture ID, resolved by the harness rather than shown to the agent;
- frozen clock;
- optional injected tool condition for dedicated robustness cases.

### Expected output

- expected team, or a small explicitly permitted set only when the policy genuinely allows it;
- expected urgency;
- expected relation ID set;
- whether manual triage is permitted/required;
- minimum required database facts.

### Metadata

- case ID and dataset version;
- split: development or confirmation;
- task family and target construct facets;
- policy rule IDs;
- difficulty band as a descriptive design label, not an estimated psychometric parameter;
- required policy capability IDs, if any;
- applicable evaluator IDs;
- predicted sensitive mutant IDs;
- negative-control mutant IDs;
- metamorphic group ID and relation, if any;
- risk/severity label;
- fixture hash.

Store human-readable datasets as YAML generated/validated through Pydantic Evals and commit the companion schema. Keep fixture data separately in versioned SQL or JSON seed files; fixtures are copied into a temporary SQLite database per execution.

## 5. Deterministic evaluators

| Evaluator | Reads | Output |
|---|---|---|
| `TeamAssignment` | Expected state and created DB row | Boolean plus expected/actual reason |
| `UrgencyAssignment` | Expected state and created DB row | Boolean plus expected/actual reason |
| `LinkSet` | Expected IDs and link table | Precision, recall, exact assertion |
| `SafeEscalation` | Manual-triage expectation and created row | Boolean |
| `TransactionIntegrity` | DB rows, constraints, request ID, audit events | Assertions for exactly-once filing and referential validity |
| `ReceiptConsistency` | Agent output and DB row/link table | Boolean |
| `PolicyUse` | Case metadata and loaded-capability/tool trace | Boolean only where a load is required; otherwise descriptive label |
| `ToolProcessMetrics` | Trace | Counts/labels for searches, reads, loads, calls, retries, errors |
| `IntegratedSuccess` | Applicable assertions declared by family | Boolean conjunction with an explanatory list of failures |

Evaluator implementation must be unit-tested against handcrafted correct and incorrect states before any model runs. Avoid an LLM judge in the MVP. Rationale quality can be retained for audit without becoming a scored primary outcome.

## 6. Metamorphic task pairs

These are secondary checks and must be generated only where the relation is valid.

| Transformation | Expected relation |
|---|---|
| Paraphrase while preserving all facts | Team, urgency, and relation set remain unchanged |
| Add emotional urgency language but no impact facts | Urgency remains unchanged |
| Change supported impact from one user with workaround to widespread outage | Urgency moves in the declared direction; team remains unchanged |
| Reorder existing-ticket search results | Relation set remains unchanged |
| Add a topically similar but causally unrelated ticket | Existing links remain and the new distractor is not linked |
| Rename synthetic customer and entity names consistently | Outcome remains unchanged |
| Remove the fact needed to disambiguate ownership | Outcome moves to manual triage if the runbook requires that fact |

Metamorphic variants belong to the same group in analysis and must not be treated as independent cases.

## 7. Authoring workflow

1. Freeze runbook rule IDs and the team/urgency ontology.
2. Draft a coverage grid before writing case prose.
3. Write development cases and fixtures.
4. Have a second reviewer derive expected outcomes from runbooks without seeing author keys.
5. Resolve disagreements by clarifying the runbook, not by inventing case-specific exceptions.
6. Run deterministic evaluator unit tests and fixture integrity checks.
7. Pilot the intact agent on development cases; repair ambiguity and harness defects.
8. Select sentinel cases based on coverage and scoring stability, not on maximizing mutation kills.
9. Author confirmation cases from the same rule blueprint using fresh wording and fixture layouts.
10. Freeze confirmation content and hashes before final mutation thresholds are run.

## 8. Baseline reliability run

Before interpreting lesions:

- run every development case at least three times;
- run sentinel cases at least five times;
- report each case's integrated and facet pass proportions with intervals;
- flag environment/tool failures separately from semantic failures;
- inspect cases with mixed outcomes and remove only demonstrated ambiguity or harness flakiness;
- record duration, model requests, tool calls, and tokens when available.

Use Pydantic Evals multi-run support for repeated executions, but preserve a stable base case ID and explicit repeat ID in exported long-form results.

## 9. Leakage and shortcut checks

- Case names visible to the agent are opaque.
- Fixture ticket IDs do not encode team or relation status.
- Tool result order is stable but not sorted by relevance label.
- Expected fields never enter prompts, runbooks, tool descriptions, or database rows visible to the agent.
- Simple keyword baselines are evaluated privately to identify cases solvable by accidental lexical cues.
- Confirmation cases do not reuse development-case templates with only noun substitution.

## 10. Dataset acceptance criteria

The suite is ready for confirmatory lesion runs when:

- all coverage minimums are met;
- every expected answer is derivable from a cited policy rule;
- all evaluator unit tests pass;
- all fixture integrity checks pass;
- no case has cross-run persistent state;
- sentinel baseline instability is understood and documented;
- metadata contains predicted and negative-control mutant mappings; and
- the confirmation split has not been used for agent or mutant tuning.

