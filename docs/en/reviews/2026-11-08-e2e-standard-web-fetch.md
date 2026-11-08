# E2E run 4 (2026-11-08) — web-fetch / standard / --prior run-1

Subject: skill at `0937936` (after cut 8). `nlink-jp/web-fetch` eight fix
commits after run-1 (source ref `aa20666…`, clean). One full pass of Phases
0–6 in the standard profile with `--prior run-1`, so the carry-over path was
exercised too. The findings live in the run directory's `REPORT.md` and
`NEEDS-VALIDATION.md`; this page keeps what the skill learned.

## Facts of the run

| Item | Value |
|---|---|
| Budget (approved) | 54 → 64 (two cost gates: 54 after reconnaissance, +10 when critic-1 added a unit and three fresh candidates still needed re-verification) |
| Actual | 56 (reconnaissance 4, hunter 19 [16 + 3 re-asks], critic 2, verifier 19 [12 + 7 re-asks], reverifier 12) |
| Coverage units | 41 → 42 (seed carried run-1's 37 units plus 4 surfaces that appeared after run-1: the CLI's stderr error JSON, the terminal-inert pass, the shared render budget, the docs tree; critic-1 added the docs tree, critic-2 stopped) |
| Carry-over | run-1's 6 confirmed and 1 needs_validation all `changed_prior` (their cited sources changed in the fix commits, so they were listed as changed prior records, not re-verified). The 9 rejected worked as suppression, and one claim (the x-user-defined remap) was in fact suppressed. 28 lead notes went to the critic |
| Candidates | 16 claims → 4 duplicate pairs folded by `merge-candidates` → 12 fingerprints (16/42 = 0.38 per unit, the constant says 0.30) |
| Verdicts | confirmed 6 (medium 1, low 4, informational 1), needs_validation 0, rejected 6 |
| Confirmed | a long run of backticks inside `<pre>` makes the fence-length loop quadratic, outside the render budget (medium); the builder's login in CHANGELOG; the CLI's stderr error JSON prints C1 and bidi controls to the terminal without the inert pass; the TOML reader's lenient grammar (trailing text dropped silently, a present empty value read as unset); unescaped markdown link text and href let a page forge links past the scheme allow-list; the `<meta content>` charset scan slices the original at an index from the lowercased copy and panics the MCP server (informational: the parser-crash rule without observation) |
| Why rejected | control belongs to the runtime 1 (the unquoted transport cause: the remote already delivers the same words on the success path); false premise 1 (recursion depth: x/net/html v0.59.0 caps the open-element stack at 512); no documented contract 2 (title bound, header values validated late); self-impact 1 (userinfo echo); no path to a user 1 (brew staged changes) |
| Re-verification | keep 10, replace 2 (reverifier-1 moved the grounds to in-target lines; reverifier-10 weakened the severity low → informational; neither strengthened, so both applied directly and were logged in `replacements.json`) |
| Allowed commands | `go test ./...`, `go vet ./...` (both exit 0, offline) |
| Notes | 137 (hardening 86, lead 33, out_of_scope 18) |
| run_status | complete |
| Absolute paths or user names in the output | none (checked with grep) |

## Measured cost (tokens per sub-agent)

The context length of each task transcript's final call (checked against one
notification's `subagent_tokens`: identical).

| Role | Count | Mean | Range |
|---|---|---|---|
| reconnaissance | 4 | ≈ 132k | 101k–148k |
| hunter | 16 | ≈ 141k | 120k–171k |
| hunter re-asks | 3 | ≈ 156k | 144k–174k |
| critic | 2 | ≈ 162k | briefs of 187 KB / 170 KB (42 units, 28 prior leads) |
| verifier | 12 | ≈ 87k | 77k–107k |
| verifier re-asks | 7 | ≈ 89k | 81k–95k |
| reverifier | 12 | ≈ 79k | 69k–97k |

About 6.2M tokens over 56 launches, against the 55–60 launches / 5.5–6M that
run 3's record estimated: on target. Inside the figure: 16 claims (12
fingerprints) against 13 expected; 10 re-asks against 7 expected (10 of 46
first returns = 22%, the constant says 15%; six of the ten came from the
parent's own prompt wording, see below). The estimate does not count
re-verifiers (E33 below).

## Deviations from the procedure (recorded)

- Re-verification (reverifier-1–9) ran before critic-1 (SKILL.md places it
  after hunting ends). Nothing in the books depends on the order; the three
  fresh records' re-verification (reverifier-10–12) ran alongside critic-2.
- hunter-8 failed twice (malformed JSON, then a missing `reviewed_paths` on
  the re-ask), so per the rule `ledger.py abandon` returned its units and a
  fresh hunter-15 was launched: first use of the abandon path, three launches
  for one set of units. hunter-15 found the charset panic.
- hunter-13's and hunter-14's returns spelled the builder's login, and
  hunter-14 an absolute audit path; both were re-asked to describe
  identifiers by file:line, never spell them. verifier-3's record referred to
  the login in prose and reverifier-1 replaced those grounds with in-target
  lines.
- Six of verifier-1–9 dropped `kind` / `scope` from trace entries. The cause
  was the parent's prompt, which named only "file, line, description", and
  `brief verifier`'s `required_fields` do not list the trace_entry /
  evidence_entry fields either. Six re-asks (`count --rerun`). verifier-18
  dropped `coverage_ids` from a rejected record and was re-asked.
- Verifier ids jump from 9 to 16 (the fresh candidates' verifiers were
  numbered ahead by candidate units). Dense ids are not a contract, so the
  books are unaffected.
- hunter-16 (docs tree) reported that Glob / Grep were unavailable and read
  files by guessed name; the parent checked with `find` that all eight files
  under docs/ had been read, and critic-2 confirmed it. Same event as run 2's
  recon-c/d and hunter-12.
- Self-reported shell use by Explore agents: verifier-16 (grep over the
  standard library), verifier-18 (one sed / grep / cat), hunter-16 (grep over
  the skill's schema.json). All reported read-only. Residual.
- The report's replacement line says "wording or line corrections only, none
  strengthening", yet reverifier-10's replacement weakened the severity (low
  → informational) (E35 below).
- The parent's zsh helpers did not word-split `set -- $v` or an unquoted
  `$VAR`, producing "no task for …" and a doubled fingerprint. Not a skill
  matter.

## Lessons → candidates for cut 9

| # | What happened | Proposed fix |
|---|---|---|
| E29 | (carried from run 3) the closing `</target-data>` tag is fixed and can be forged | Put the nonce on the closing tag too (`</target-data-N>`); it changes every prompt's contract, so decide at this cut |
| E30 | A prior needs_validation record became `changed_prior` after the fix, but its unit kept `prior_needs_validation` | `seed --prior` marks it `prior_needs_validation_changed_source`, as for confirmed |
| E31 | Six verifiers dropped trace `kind` / `scope` (the parent's wording) | `brief verifier|reverifier` includes the `trace_entry` / `evidence_entry` required fields in `required_fields`, and SKILL.md's verifier prompt lists the brief's field names |
| E32 | Two hunters spelled the builder's login and an absolute audit path | Every role's contract: describe personal identifiers and local paths by file:line, never spell them. `ledger.py record` / `findings.py add` refuse a return that contains the operator's login (`getpass.getuser()`) or an absolute local path (a script control) |
| E33 | `estimate` does not count standard's re-verifiers (`reverifiers: None`) | Add decided plus expected candidates as re-verifiers |
| E34 | Hunters that report no listing read files by guessed name (runs 2 and 4) | `brief hunter` prints the file list under `starting_paths` (in-target, relative, capped) |
| E35 | The report's replacement line calls a weakening replacement a wording fix | `compile.py` words the line by the kind of difference recorded in `replacements.json` (wording / weakening) |
| E36 | Abandoning a twice-failed hunter and launching a fresh one took three launches | Per the rule. Whether the estimate's re-ask rate should include one abandonment waits for more measurements (56 of 64 this run) |

The verifiers worked as designed: of the candidates the hunters called
confirmed, the verifiers rejected 4; of the 3 called needs_validation, 1 was
confirmed (the charset panic, settled by reading the standard library and
x/net/html) and 2 rejected (recursion depth: the dependency source refutes
the premise; the unquoted cause: the control belongs to the runtime). All 6
rejections were downgraded to hardening notes. The re-verifiers replaced 2 of
12 records (a weakening and a wording fix), strengthening none.

## Phase 3 in total (four runs)

| Run | Target / profile | Launches | Tokens | confirmed / nv / rejected |
|---|---|---|---|---|
| 1 | webhook-relay / quick | 29 | ≈ 2.6M | 5 / 2 / 7 |
| 2 | webhook-relay / standard --prior | 42 | ≈ 3.9M | 0 / 2 / 7 |
| 3 | web-fetch / quick | 43 | ≈ 4.6M | 6 / 1 / 9 |
| 4 | web-fetch / standard --prior | 56 | ≈ 6.2M | 6 / 0 / 6 |

Both standard runs landed inside their estimates (run 2 at two thirds, run 4
on target). Carry-over from quick to standard worked for the first time in
run 4: one of run-1's rejections suppressed a re-report, and the seven fixed
records cost no re-verification and were listed as changed prior records.

## Adopted in cut (9) (2026-11-08)

E29–E35 adopted (101 tests); E36 waits for more measurements. E29: `run.py nonce`
prints both tags and SKILL.md wraps with `<target-data-N>…</target-data-N>` (the
closing-tag breaking in architecture.md stays as defence in depth). E30: `seed --prior`
marks `prior_needs_validation_changed_source`. E31: the verifier's and re-verifier's
briefs list the required fields of `trace_entry` and `evidence_entry`, and the SKILL
contract reads the field names from the brief. E32: `_contract.personal_identifier_errors`
(the operator's login as a whole word when three characters or longer, absolute local
paths by pattern) runs where `record`, `merge-critic`, `architecture`, `findings.py add`
and `note` take a return, and every role's contract says describe at file:line, never
spell. E33: the standard estimate adds one re-verifier per decided record, minus those
launched. E34: `brief hunter --target TARGET` carries the files under each unit's
starting paths (cap 400, links by name, `.git` skipped). E35: `findings.py add --replace`
logs `weakened` and the report's replacement line counts strengthening, weakening and
wording apart.
