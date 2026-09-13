# Eval artifact contract

Supplying `--output PATH.json` to `python -m eval_mutation.evals` produces a native
Pydantic Evals report plus three analysis artifacts sharing the same filename stem.

## Per-run rows

The `.rows.jsonl` file has one row for every case repeat, including task failures.
Each row retains:

- stable case ID plus Pydantic's repeated-case name and explicit repeat index/count;
- split, task family, construct facets, metamorphic group, and fixture hash;
- expected and actual team, urgency, relation IDs, and manual-triage behavior;
- every assertion, score, label, metric, reason, and evaluator version;
- task/total duration and trace/span IDs;
- task failure category, message, and stack trace when execution fails.

This is the primary analysis input. Summary values must be reconstructable from these
rows rather than recovered from console output.

## Slice summary

The `.summary.json` file groups rows by:

- overall run;
- task family;
- target construct facet;
- expected team;
- expected urgency;
- fixture hash; and
- exception type, including `none` for completed executions.

Every slice reports completed and failed run counts, applicable denominators and pass
rates for each assertion, and means plus denominators for numeric process scores. A failed task does not
become a failed semantic assertion: it is counted as an execution failure with no
assertion denominator.

## Run manifest

The `.manifest.json` file records enough provenance to decide whether two result sets
are comparable: dataset and selected cases, fixture/runbook/source hashes, evaluator
versions, full agent configuration, Ollama model digest when discoverable, installed
package versions, Python/platform/CPU information, Git commit and dirty state, repeat
and concurrency policy, observability state, failure counts, and hashes of the other
artifacts.

The current configuration is explicitly recorded as `baseline` with no mutation. The
first paired mutation runner will extend this same versioned contract with activation
and pair identifiers rather than inventing a second incompatible result format.
