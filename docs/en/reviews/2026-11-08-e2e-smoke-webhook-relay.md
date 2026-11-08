# E2E smoke (2026-11-08) — webhook-relay / quick

Subject: skill at `cac8de8` (after the two verification rounds). One full pass
of Phases 0–6 over the organisation's real repository `nlink-jp/webhook-relay`
(source ref `5ba3625b…`, clean tree) in the `quick` profile, driven by the
parent exactly as SKILL.md says. Goals: (1) do the scripts and the procedure
hold on a real repository, (2) measure one pass and re-estimate the other
three runs (web-fetch quick / standard, webhook-relay standard). The findings
themselves live in the run directory's `REPORT.md`; this page keeps only what
the skill learned.

## Facts of the run

| Item | Value |
|---|---|
| Budget (approved) | 34 launches |
| Actual | 29 (reconnaissance 5 [4 real], hunter 10 [7 + 3 re-asks], critic 2 [1 + 1 re-ask], verifier 12 [11 + 1 re-ask]) |
| Coverage units | 21 → 26 (the critic added 5 as deferred and reassigned 1 → deferred) |
| Candidates | 14 (3 pairs sharing one root cause) |
| Verdicts | confirmed 5 (medium 1 / low 4), needs_validation 2, rejected 7 (3 duplicates, 4 downgraded to hardening) |
| Allowed commands | 0 (`go test` reaches the network, ADC and the build cache under HOME) |
| run_status | complete |
| Absolute paths in the output | none (`/Users/<login>/...` appears only as a verifier's example) |

## Measured cost (tokens per sub-agent)

| Role | Count | Mean | Range |
|---|---|---|---|
| reconnaissance | 4 | ≈ 88k | 82k–98k |
| hunter | 7 | ≈ 86k | 69k–136k (the whole-repository unit cost 136k) |
| critic | 1 | ≈ 100k | — |
| verifier | 11 | ≈ 91k | 81k–102k |
| re-asks (SendMessage continuation) | 5 | ≈ 100k | 73k–146k (the context is re-sent, so dearer than a first launch) |

One pass cost about 2.6M tokens. First returns were refused 5 times out of 24
(21%), and those re-asks were about a fifth of the total.

## Deviations (for the record)

- recon-d was counted twice (`count` cannot decrement by design): 4 real, 5 counted.
- recon-d returned absolute paths in `files`; relativised on save.
- The critic's input numbered the units instead of giving the `coverage_id`
  strings; the returned `reassign_ids` said "17" and `merge-critic` refused.
  Fixed by one re-ask.
- Each duplicate pair went to one verifier, which returned a `verdicts: [...]`
  array. That shape is outside the contract, so the parent split it into one
  record per file under `agents/to-add/` before `digest` → `add` (parent-side
  extraction).
- Verifier and critic contracts referenced the schema parts of `schema.json`
  by name instead of pasting them as SKILL.md asks.

## Lessons → candidates for cut 6

| # | What happened | Proposed fix |
|---|---|---|
| E1 | `count --agent` silently counts the same id twice | refuse an already-registered id without a re-ask flag |
| E2 | reconnaissance returns absolute paths | the recon contract says repository-relative only; `record`/save refuses |
| E3 | two hunters refused: `reviewed_paths` ≠ union of checks | `record` accepts ⊇ and stores the union, or the contract text is fixed |
| E4 | a `.gitignore:…` fingerprint refused for its leading `.` | FINGERPRINT_RE allows dot-files |
| E5 | `estimate` counts one hunter per unit and overestimates | the estimate reflects the grouping (3–4 units per hunter) |
| E6 | a Go target can produce no `existing_test` evidence under the boundary | `run.py exec` provides a GOCACHE under the run and allows only that write |
| E7 | the same root cause arrives from several hunters under different fingerprints | `ledger.py merge-candidates` before verification (duplicates recorded as rejected), or `add` accepts `verdicts[]` |
| E8 | the parent can paraphrase the ledger for the critic | `ledger.py brief critic` prints the critic's input with the coverage_id strings verbatim |
| E9 | a verifier trace with two sinks | the contract says "one sink, last" (the validator already refuses) |
| E10 | two leftover "Refines generic `…`." sentences in cli.md | remove |
| E11 | verifier notes carry leads for the next run (bucket-name squatting, `--set-env-vars` comma splitting, zip uid/gid) | add a note kind `lead` that the next run's `seed` picks up |
| E12 | a unit stays `candidate` after `decide` | the report reads "candidate (decided)" |

The verifiers worked as designed: four hunter `confirmed`s were downgraded to
rejected + hardening note by citing severity.md "What is not a finding", and
both `needs_validation`s name the same library fact (the meaning of
`Writer.Close` in storage v1.62.0) as the blocker.

## Re-estimate of the other three runs (from the measurements)

| Run | Basis | Launches (approx.) | Tokens (approx.) |
|---|---|---|---|
| webhook-relay standard | same 21 + 6 units, two hunter waves, 2 critics, re-verification | 40–45 | 3.5–4M |
| web-fetch quick | 6.2k lines of Go (4× webhook-relay), plus the MCP-server class | 35–40 | 3.5M |
| web-fetch standard | the standard profile of the above | 60–70 | 6M |

The 21% re-ask rate is included. Fixing E3, E4, E8 and E9 in cut 6 first
should at least halve the re-asks.
