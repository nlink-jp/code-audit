# Severity and confidence

Only a `confirmed` record carries a severity. `needs_validation` is a
source-grounded hypothesis blocked by a fact that reading cannot settle; it
has blockers and a plan, never a score. `rejected` has a reason.

`scripts/findings.py validate` fixes the vocabulary below and rules 1 and 2;
`findings.py add` enforces rule 3 on every new record. The words are the whole scale: do not invent intermediate values.

## Likelihood — `severity.likelihood.score`

| Score | Meaning |
|-------|---------|
| `high` | The lower-trust principal reaches the path with ordinary use of the interface and no unusual precondition |
| `medium` | Reaching the path needs a specific but realistic precondition: a particular configuration, a second feature enabled, a race the attacker can retry |
| `low` | Reaching the path needs sustained effort, an unlikely combination, or cooperation from another principal |

## Impact — `severity.impact.score`

| Score | Meaning |
|-------|---------|
| `critical` | An unauthenticated actor gains code execution, full data-store access, or takeover of arbitrary accounts |
| `high` | An actor fully defeats an explicit security control with real consequences: authentication bypass, cross-tenant read or write, stored script execution affecting other users, authenticated code execution, an unauthenticated stop of a shared service |
| `medium` | A real boundary violation with limited blast radius, uncommon preconditions, or consequences confined to a narrow resource set |
| `low` | Disclosure of non-secret internals, or an effect that needs sustained effort for minimal gain |
| `informational` | A confirmed but minimal-impact observation, useful mainly as a prerequisite inside a larger finding |

The high/medium discriminator: does the demonstrated result fully defeat an
explicit control for an action with real consequences, or only weaken it?
If the concrete damage cannot be stated, the impact is lower than it feels.

## Overall — `severity.overall`

Same vocabulary as impact. Overall is likelihood × impact judged by the
verifier, under one rule the validator enforces:

**Rule 1 — overall never exceeds impact.** A likely path to a small effect
is a small finding. Order: `informational` < `low` < `medium` < `high` <
`critical`.

## Confidence — `confidence.score`

| Score | Meaning |
|-------|---------|
| `high` | The result was observed: an existing test under `checks/` shows it, and the verifier reproduced the reading independently |
| `medium` | The path is established from source by two independent readers (hunter and verifier) and the preventing layers (handler registration, upstream middleware, configuration defaults) were reconstructed and found absent |
| `low` | The path is established from source but a preventing layer could not be fully reconstructed, or the readers disagreed on a detail that does not change the verdict |

**Rule 2 — source-only evidence caps confidence at `medium`.** A record
whose `evidence_kind` is `source` cannot claim `high` confidence: reading
source yields a hypothesis, and the report shows the evidence kind beside
every confirmed finding so the reader sees which ones were observed.

## Whose act, and whose decision — `path_actor`, `specified_in`

Every confirmed record of this version answers two questions before it
carries a severity (the first audit of an agent runtime rated a documented,
operator-composed path `high`; the fix was withdrawn after two review rounds
— knowledge `development-process.md#Before fixing an audit finding, ask whose
act makes it happen and whether the behaviour is specified`):

| Field | Values | Meaning |
|-------|--------|---------|
| `path_actor` | `unasked` | The path runs with no act of the operator's beyond ordinary use: a lower-trust principal (file author, server, model) reaches the sink by itself |
| | `operator_composed` | The operator has to compose the path themselves — pipe third-party text into the command channel, type the command, pass the flag — in the way `curl … \| bash` is composed |
| `specified_in` | a record | An ADR, design document or reference of the target that decided this behaviour, cited as the target names it (`ADR-0055 §3`, `docs/reference/interface.md#Piped input`) |
| | `none` | No record of a decision was found after looking where the target keeps them |

**Rule 3 — an operator-composed path whose behaviour a record decided is
not a finding.** `findings.py add` refuses such a `confirmed` record. The
verifier returns `rejected` with a `reason` naming the record, and adds a
`documentation` note when the decision is not stated where the operator
reads (README, reference, `--help`): that gap is the owner's to close, and
the rejected fingerprint suppresses the claim in the next run. The rule does
not cover an `unasked` path: a documented decision that a lower-trust
principal can reach unasked is still a finding, and the record is cited so
the owner sees which guarantee it broke. `operator_composed` with no record
stays a finding; say in `likelihood.reason` what the operator must do.

## What is not a finding

- A missing best practice with no affected principal or resource is a
  hardening note (`notes.json`, kind `hardening`), not a record.
- If layer A prevents the attack, the absence of layer B is a hardening
  note. Defense in depth is advice, not a vulnerability.
- Self-impact, intended same-principal authority, and a guessed deployment
  behaviour are not boundary violations.
- An operator-composed path whose behaviour a record decided (rule 3): a
  `rejected` record naming it, plus a `documentation` note when the decision
  is not stated where the operator reads.
- A parser crash is `informational` unless a stronger effect was observed.
