# First production run (2026-11-09) — gem-agent / standard / no prior

Subject: skill v0.1.0 (after cut 9). `nlink-jp/gem-agent` is an LLM agent
runtime with 108 ADRs (source ref `a033b76…`, clean). Another session ran
Phases 0–6 in the standard profile; the owner (the same user) triaged the
findings and released v0.100.0 / v0.100.1. The findings live in the run
directory's `REPORT.md` and `NEEDS-VALIDATION.md`; the owner's decisions are
gem-agent's ADR-0109 to ADR-0113. This page keeps what the skill learned.

## Facts of the run

| Item | Value |
|---|---|
| Budget (approved) | 140 (the estimate at a candidate rate of 0.30 was about 86; raised during the run) |
| Actual | 138 invocations (reconnaissance 4, hunter 27, critic 1, verifier 55, reverifier 51) |
| Coverage units | 71 (no prior; every unit fresh) |
| Verdicts | confirmed 37 (high 2, medium 8, low 23, informational 4), needs_validation 9, rejected 7, merged 9 |
| Candidate rate | 53 decided + 1 pending + 9 merged = 63 claims / 71 units = over 0.75 (more than twice the constant 0.30) |
| Re-verification | 10 replacements (1 weakening, 9 wording; no strengthening) |
| Notes | 287 |
| run_status | **incomplete** (`budget_reserved_for_verification`: 43 candidate units of which 42 decided, 1 blocked, 16 unassigned surfaces) |
| Owner's triage | one high withdrawn as **specified** (ADR-0110), three medium **accepted** with reasons (ADR-0113), the rest fixed in v0.100.0 / v0.100.1 |

## What the handling of the findings showed

- **One high was the documented specification.** "Piped stdin without `-p`
  runs as the operator's input, `!` commands included" is the script path
  ADR-0055 §3 decided; nothing happens unless the operator composes the pipe
  themselves (`curl … | bash` has the same shape). The owner implemented a
  refusal and a `--script-stdin` flag, ran two review rounds, and withdrew
  it. The verifier's record wrote "documented choice" in `intended_behavior`
  and still scored high. Two questions decide it: whose act makes the path
  happen, and which record decided the behaviour (knowledge
  development-process, "Before fixing an audit finding, ask whose act makes
  it happen and whether the behaviour is specified").
- **Three medium findings were accepted with reasons** (reads inside
  `agentic_file_search` outside hooks and `always`; ancestor `AGENTS.md`
  outside the trust question; the file tools' verdict and write seeing
  different links). The owner recorded them as residuals in ADR-0113 and
  stated them where the operator reads. The next run with `--prior run-1`
  would queue them as `prior_confirmed_same_source` for re-verification and
  report them again — the books had no place for an acceptance.
- **The high that was right to fix** (the approved lanes' cache inside the
  read lane's writable scratch) needed no act of anyone and broke ADR-0084's
  guarantee. The same two questions separate the cases.
- **The budget ran out and the run ended incomplete.** The rate 0.30 was
  calibrated on two standard runs *after* a prior; a standard run with no
  prior has every unit fresh, like quick. Measured: over 0.75 (quick's fresh
  rates were 0.43 and 0.48). On 71 units the gap was about 50 invocations.
- The knowledge base gained four lessons the same day (the two questions;
  where a privileged build's cache goes — the existing class's source "at the
  session scratch" was measured insufficient; an approval prompt carries the
  whole call; a lane-writable directory reused on resume is refused when it
  became a link). The RFP says classes follow new lessons at a release.

## Lessons → candidates for cut 10

| # | Observed | Proposed fix |
|---|---|---|
| E37 | A documented behaviour of an operator-composed path scored high | A confirmed record answers `path_actor` (unasked / operator_composed) and `specified_in` (the deciding record, or none); operator_composed with a record is not a finding (rule 3: `findings.py add` refuses it → `rejected` plus a `documentation` note) |
| E38 | The estimate priced a standard run with no prior at half of quick's rate; 140 was not enough | Split the candidate rate by whether the unit has a prior, not by profile (fresh 0.60 / prior 0.30). Print `shortfall` and say at the cost gate that a lower budget ends the run incomplete |
| E39 | An owner-accepted finding has no place in the books and is re-verified and re-reported next run | `findings.py accept --fingerprint --record --reason` (`dispositions.json`, append-only, `--withdraw` reverses). `seed --prior` lists accepted records as `accepted_prior`; unchanged sources are neither re-verified nor re-reported (`record` suppresses the same claim), changed sources are hunted under `prior_accepted_changed_source` |
| E40 | Four knowledge lessons of 2026-11-09 are not in the classes | agent-runtime.md: the cache class gains the new source and "a denial by name is a second line"; new classes "Approval dialog shows less than the call" and "Lane-writable directory reused on resume". generic.md's resource class cites the x/net/html quadratic allocation (2026-11-08). "Ask before fixing" is the source of severity.md rule 3 |

## Adopted in cut (10) (2026-11-09)

E37–E40 adopted (107 tests green). E37: `schema.json` keeps the two fields
optional (so a prior run's records still load), `findings.py add` requires
them of every new confirmed record and enforces rule 3; the briefs'
`required_fields` list them; the report prints "act needed / deciding
record" under each finding and has a section for `documentation` notes.
E38: `estimate` returns `fresh_units`, `prior_units` and `shortfall`, and
`candidates_per_unit` is a two-entry table. E39: `dispositions.json` is
owned by `findings.py`; the report shows "Owner's disposition" under the
finding and the next run's report lists "Prior findings the owner accepted".
E40: 54 classes, 119 citations verified against the knowledge checkout.

## Commit-time review (2026-11-09, independent read-only sub-agent)

Seven findings plus nits; six adopted, one (chaining) answered in the text.
The reviewer reproduced each with a throw-away script of its own.

- **Adopted**: a prior run's dispositions, lead notes and records were not
  checked for the operator's login or absolute paths and reached the report
  → `load_prior` now drops all three on `personal_identifier_errors`. With
  two priors one fingerprint sat in both `carried` and `accepted_prior` →
  "the latest prior's word wins" is applied per fingerprint across every
  bucket (carried / changed_prior / accepted_prior / suppressed), one entry
  per fingerprint. `is_fresh` priced `prior_deferred` / `prior_out_of_scope`
  units at the prior rate although nothing hunted them → counted as fresh. A
  broken `dispositions.json` of the run itself made compile raise KeyError →
  validated on load as an owned file, stopping the script. `findings.py
  validate` did not re-check rule 3 → re-applied to any record carrying
  either field. `dispositions.json` missing from the tests' OWNED_FILES →
  added (and SKILL.md names the owning script beside it). Nits: `status`
  prints `accepted_prior`; the date is checked as a calendar date; the class
  texts gained the measurements they had dropped (expand tabs, JSON for
  non-strings, state the omission on the first line; cut before Parse, a
  failed Parse is "no tree").
- **Answered in the text**: an acceptance works for one run only (run-2 lists
  it without holding the record, so a run-3 with `--prior run-2` alone hunts
  it as new). SKILL.md now says an acceptance lives in the run where the
  owner logged it and applies while that run is among the priors — Phase 0
  already says to pass every earlier run — and no mechanism copies it
  forward (that would make two authoritative copies of the owner's record).
