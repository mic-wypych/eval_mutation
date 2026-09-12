# Mutation and Intervention Experiment

## 1. Experimental question

Does the eval suite respond to controlled agent/scaffold degradations in the pattern predicted by its construct model—large effects on theoretically relevant task families and smaller effects on predeclared negative-control families?

The primary artifact is a lesion-by-task-family effect matrix. A scalar mutation score is secondary and must never replace the matrix.

## 2. Mutant design rules

Every mutant must be:

- tied to one causal hypothesis and one construct facet;
- implemented as a small, reversible configuration-selected change;
- named and versioned;
- independently activation-tested;
- plausible enough to represent a meaningful failure mode;
- assigned predicted task families and negative controls before results are seen; and
- classified after trace review as effective, equivalent/ineffective, broad, or unexpectedly selective.

Mutants must not modify eval cases, expected answers, evaluators, result aggregation, or confirmation fixtures.

## 3. Initial mutant catalog

| ID | Target | Intervention | Predicted strongest effect | Predeclared negative controls |
|---|---|---|---|---|
| M1 | F1 Routing | Delete one routing precedence block, such as compromise-over-access and money-moved-over-UI rules | T2 and relevant T8 cases; `team_correct` | T3–T4 urgency-focused cases with explicit teams; link scores |
| M2 | F2 Urgency | Replace the impact thresholds with a locally plausible but wrong downgrade rule | T3 and relevant T8; `urgency_correct` | T1 routine routing; team and link scores |
| M3 | F3 Retrieval | Degrade search to omit the best matching candidate when distractors exist | T5 and relevant T8; link recall | T1–T4 and T7; team/urgency |
| M4 | F3 Relation judgment | Remove the “shared topic is insufficient” rule or add an instruction to link topically similar tickets | T6 and relevant T8; link precision/exactness | T1–T4; team/urgency |
| M5 | F4 Policy acquisition | Make one deferred runbook load return an empty or stale body while leaving the capability catalog intact | Policy-dependent T2/T3/T7/T8 cases | Routine T1 and obvious T4 cases |
| M6 | F5 Transaction | Introduce a bounded filing defect, such as dropping supplied relation IDs while still returning success | T5/T8 transaction and link state | Correct team/urgency fields in the same cases; no-link T1/T6 cases |
| M7 | Broad positive control | Remove all runbooks and make ticket-search tools unavailable | Broad integrated-success drop | None; this is a pipeline sensitivity check, not construct evidence |
| M8 | Negative/no-op control | Change a comment, internal identifier alias, or semantically equivalent prompt formatting with verified identical runtime behavior | No meaningful effects | All families |

For M1 and M2, retain both the original and mutated policy text in the run manifest. For tool mutants, log an activation marker that proves the altered branch executed. Without activation evidence, a survivor is uninterpretable.

## 4. Severity ladder

After the first catalog works, add at most two severities for selected facets:

- mild: one exception/ranking behavior is degraded;
- moderate: a sub-policy or subset of search results is corrupted;
- severe: the whole facet support is unavailable.

A credible suite should often show monotonic degradation on affected tasks. Severe global collapse is less informative about discriminant validity than a localized mild/moderate response.

## 5. Hypothesis matrix

Before confirmatory runs, create a machine-readable expectation table whose cells are:

- `target`: meaningful degradation predicted;
- `spillover_allowed`: secondary dependency makes some degradation plausible;
- `negative_control`: practically small effect predicted;
- `not_applicable`: no interpretable hypothesis.

The expected high-level block structure is:

| Mutant | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 Routing | control | target | control | control | control | control | target subset | target |
| M2 Urgency | control | control | target | target subset | control | control | target subset | target |
| M3 Retrieval | control | control | control | control | target | spillover | control | target |
| M4 Relation rule | control | control | control | control | spillover | target | control | target |
| M5 Policy load | control | target | target | control | spillover | spillover | target | target |
| M6 Filing defect | control subset | control subset | control subset | control subset | target | control subset | control subset | target |

Replace “subset” with exact case IDs and exact scored facets in the preregistration.

## 6. Execution design

### Stage A: engineering and screening

1. Run baseline reliability on development cases.
2. Activation-test each mutant with a purpose-built development probe.
3. Run baseline and every mutant on the 12-case sentinel set, three repeats per configuration.
4. Use results to repair implementation errors, identify equivalent mutants, and narrow hypotheses.
5. Do not report this stage as confirmatory validity evidence.

### Stage B: targeted confirmation

For each non-equivalent mutant:

1. select all confirmation cases pre-tagged as targets for that mutant;
2. select a balanced pre-tagged negative-control set;
3. run baseline and mutant five times per case;
4. interleave baseline and mutant order within time blocks;
5. pair observations by case, repeat index, fixture, and seed where the model honors seeds;
6. export one long-form row per execution and facet score.

If compute is tight, reduce the number of active mutants before reducing target/control coverage. Do not use the broad mutant as a substitute for targeted confirmation.

## 7. Estimands

For task family or case group `i` and mutant `j`, define the primary effect as the paired risk difference:

`D[i,j] = mean(baseline facet success - mutant facet success)`.

Report:

- point estimate and interval for every interpretable matrix cell;
- target-block mean effect;
- negative-control-block mean absolute effect;
- target-minus-control contrast;
- integrated-success effects separately from facet-specific effects;
- numerators, denominators, exception counts, and activation rate.

For link handling, report precision and recall effects separately. A single exact-link pass can hide whether a mutant creates false positives or false negatives.

## 8. Pilot decision rules

Freeze the exact statistical implementation before Stage B. A suitable Bayesian pilot rule is:

- **target detected:** posterior probability that target-block degradation exceeds 0.15 is at least 0.90;
- **localized response:** posterior probability that target degradation exceeds negative-control degradation by at least 0.10 is at least 0.90;
- **broad response:** target detected, but the localization condition fails and negative-control point degradation is at least 0.10;
- **survivor:** target detection condition fails despite verified mutant activation;
- **ineffective/equivalent:** activation or trace review shows the intended capability was not materially changed; exclude from mutation-score denominators but retain in the report.

These are research thresholds, not universal standards. Include sensitivity results under nearby thresholds. With the small pilot, absence of evidence should be reported as inconclusive rather than proof of specificity.

Use a hierarchical binary model or case-clustered bootstrap that respects repeated runs within cases. Do not treat all execution rows as independent. The case, not the repeated sample, is the main generalization unit.

## 9. Mutation summary measures

If a scalar is desired, report several counts rather than one opaque percentage:

- targeted mutants detected / non-equivalent targeted mutants;
- targeted mutants with localized response / detected targeted mutants;
- broad mutants detected / broad controls;
- no-op controls falsely detected / no-op controls;
- predicted target cells supported / interpretable target cells;
- predicted negative-control cells with practically small point effects / interpretable control cells.

Never claim that a high killed-mutant fraction validates the construct if effects are broad or off-target.

## 10. Trace-review protocol

Blind the reviewer to baseline/mutant identity where practical. Review:

- all unexpected target survivors;
- all large negative-control effects;
- all tool exceptions and invalid outputs;
- a random sample of expected kills and expected nulls.

Assign one reason code: expected causal path, compensating behavior, mutant not activated, equivalent mutation, task mis-tagged, shared dependency, scorer defect, fixture leakage, provider instability, or unknown. Changes prompted by this review apply to the next version and are re-tested on fresh confirmation cases.

## 11. Interpretation examples

- M3 lowers link recall on T5 but leaves routing/urgency and T1–T4 stable: convergent and discriminant evidence for the linking task interpretation.
- M1 lowers every task family: the routing policy is a shared scaffold prerequisite or the mutation broke the whole prompt; this kills the mutant but weakens construct specificity.
- M2 changes no urgency outcomes and traces show the model ignored both original and mutated runbooks: the mutant is ineffective for the intended causal claim.
- M8 is repeatedly “killed”: the run process or thresholds are too noisy, so targeted conclusions are not yet trustworthy.

