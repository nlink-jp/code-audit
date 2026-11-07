# Severity and confidence

Only a `confirmed` record carries a severity. `needs_validation` is a
source-grounded hypothesis blocked by a fact that reading cannot settle; it
has blockers and a plan, never a score. `rejected` has a reason.

`scripts/findings.py validate` fixes the vocabulary below and the two rules
at the end. The words are the whole scale: do not invent intermediate values.

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

## What is not a finding

- A missing best practice with no affected principal or resource is a
  hardening note (`notes.json`, kind `hardening`), not a record.
- If layer A prevents the attack, the absence of layer B is a hardening
  note. Defense in depth is advice, not a vulnerability.
- Self-impact, intended same-principal authority, and a guessed deployment
  behaviour are not boundary violations.
- A parser crash is `informational` unless a stronger effect was observed.
