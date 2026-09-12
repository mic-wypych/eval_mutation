# Agent and Domain Specification

## 1. Intended workflow

The agent receives one inbound support request and a case-scoped ticket store. It must:

1. understand the request;
2. load any relevant routing or urgency runbook that is not already in context;
3. inspect existing tickets when a possible relation is material;
4. choose exactly one destination team and one urgency level;
5. link only tickets supported by the relation policy;
6. file exactly one new ticket; and
7. return a concise receipt of what it did.

The database mutation is the work product. A correct narrative without the correct database change is a failure.

## 2. Input contract

Each inbound request has the following fields:

| Field | Meaning |
|---|---|
| `request_id` | Stable idempotency key supplied by the harness |
| `title` | Short user-written title |
| `body` | Free-text description |
| `customer_id` | Synthetic customer identifier |
| `submitted_at` | Frozen timestamp used by time-sensitive rules |
| `channel` | One of email, chat, monitoring, or internal |
| `account_tier` | Standard or enterprise; relevant only where a policy explicitly says so |

Cases may omit useful facts from title/body. The agent may choose `manual_triage` when the routing policy says the evidence is insufficient. It must not infer hidden case metadata.

## 3. Destination teams

| Team | In scope | Important boundary |
|---|---|---|
| `identity_access` | Login, MFA, account lockout, permissions, SSO configuration | Suspicious takeover or exposed credentials route to security/privacy |
| `billing_payments` | Charges, invoices, refunds, subscriptions, payment failures | A product defect merely affecting a billing screen routes to product/technical unless money moved incorrectly |
| `product_technical` | Defects, API/integration failures, availability symptoms, data-processing failures | Credible vulnerability or unauthorized disclosure routes to security/privacy |
| `security_privacy` | Account compromise, vulnerabilities, credential exposure, unauthorized disclosure, privacy rights | Ordinary password reset without compromise routes to identity/access |
| `product_feedback` | Feature requests, non-defect UX feedback, documentation suggestions | A currently broken promised behavior routes to product/technical |
| `manual_triage` | Insufficient, incoherent, or genuinely conflicting evidence | Not a convenience fallback for difficult but answerable cases |

Only these values are valid. The full edge-case rules live in on-demand Markdown runbooks; the system prompt contains the workflow and the catalog descriptions, not all policy details.

## 4. Urgency scale

| Level | Operational definition | Examples |
|---|---|---|
| `P0_critical` | Active or imminent severe harm needing immediate response | Active data disclosure, confirmed account takeover in progress, widespread production outage, irreversible data loss underway |
| `P1_high` | Serious blocked work or high-impact degradation without the P0 threshold | Enterprise production workflow blocked, repeated payment failure preventing service, many users affected with a workaround absent |
| `P2_normal` | Ordinary actionable support work | Single-user defect with workaround, invoice correction, routine access problem |
| `P3_low` | Non-blocking improvement or informational request | Feature request, documentation suggestion, cosmetic issue |

User words such as “urgent,” capitalization, anger, account tier, or repeated punctuation do not alone increase urgency. The urgency runbook is authoritative. When evidence is incomplete, choose the highest level directly supported by facts rather than inventing impact.

## 5. Related-ticket policy

A ticket may be linked when the existing ticket is evidence of the same incident, defect, request, or root cause. Shared team, shared product area, similar vocabulary, or the same urgency is not enough.

The fixture will contain:

- true related tickets;
- topically similar distractors;
- stale/resolved tickets that may or may not be linkable under the runbook;
- tickets in another team that share an incident; and
- cases with no relation at all.

The agent should search when the inbound request contains an incident identifier, error code, affected component plus distinctive symptom, explicit reference to earlier contact, or another meaningful relation cue. It should not enumerate every team by default.

## 6. Tool contract

All tools return typed results with stable error codes. Tool descriptions explain mechanics, not the correct decision for an eval case.

| Tool | Purpose | Required behavior |
|---|---|---|
| `search_tickets` | Find candidate existing tickets by text and optional filters | Read-only; returns bounded summaries and stable ordering |
| `get_ticket` | Inspect one candidate in full | Read-only; records the requested ID in the trace |
| `list_team_tickets` | Browse recent work for one team | Read-only; bounded page size; mainly useful when a case supplies a team/incident cue |
| `file_ticket` | Create the new ticket with team, urgency, summary, rationale, and optional relation IDs | Idempotent on `request_id`; validates enums and relation IDs; exactly one created row at most |
| `link_tickets` | Add or correct links after filing | Idempotent; only accepts the newly filed ticket as source; preserves an audit event |

On-demand runbooks are exposed through Pydantic AI deferred capabilities with stable IDs. If the selected local model cannot reliably use deferred capabilities, the documented compatibility fallback is one ordinary `load_runbook` tool. The experiment must freeze one mechanism; results from the two mechanisms are not pooled.

## 7. On-demand runbooks

Start with these Markdown policy artifacts:

| Capability ID | Contents |
|---|---|
| `routing-policy` | Full team definitions and edge-case precedence |
| `urgency-policy` | P0–P3 criteria, non-signals, and tie-breaking |
| `relation-policy` | Linkable relations, distractors, stale-ticket rules, and search expectations |

Loading all three on every task is allowed but inefficient. The eval records which policies were loaded and whether the task actually required them. Policy loading is supporting response-process evidence, not a success criterion on routine cases unless the case explicitly requires a non-obvious rule.

## 8. Structured receipt

The final receipt should expose:

- created ticket ID;
- selected team and urgency;
- linked ticket IDs;
- a short rationale grounded in request facts and, when used, policy;
- an uncertainty/escalation note when assigned to manual triage.

The receipt is checked for schema validity and consistency with the database. Team, urgency, and links are scored from database state to avoid rewarding unsupported prose.

## 9. Execution envelope

Freeze these parameters per experiment:

- one model and exact model build/digest;
- zero or low temperature, plus explicit seed if the provider/model honors it;
- one inbound request per fresh run;
- maximum model requests and tool calls;
- no retry after a semantically valid but wrong completion;
- bounded framework/provider retries only for transport failures;
- local, frozen clock and database fixture;
- no network access other than the local model endpoint;
- no conversation history from prior cases.

The primary estimand is single-attempt success within this envelope. A future retry-capable production policy would be a different construct and should be evaluated separately.

## 10. Explicit non-goals

- composing customer replies;
- solving the underlying support problem;
- assigning individual employees;
- predicting time-to-resolution;
- free-form project management;
- semantic embeddings or external search;
- multi-agent delegation;
- learning from earlier eval cases.

