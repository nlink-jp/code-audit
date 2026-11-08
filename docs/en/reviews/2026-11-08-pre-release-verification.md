# Pre-release independent verification (2026-11-08) — triage of the findings

Subject: `a4be51a` (Phase 1 complete). Three verifiers in separate contexts
(design conformance and model-facing quality / script correctness and
security / hunting-class fidelity) ran read-only; the findings are grouped by
root-cause class. The author triaged them; nothing was applied automatically.
V-1 and F-1 were reproduced by the author in a separate environment.

Legend: **adopt** = fixed in cut (4) / **document** = recorded as a residual in
the RFP or README rather than in code / **defer** = decided in Phase 2 or
later / **reject** = with the reason.

## A. Controls that are still prose (the scripts do not hold them)

| # | Finding | Severity | Decision | Fix |
|---|---------|----------|----------|-----|
| A1 | The cost gate's approval and budget do not reach `assign`; the approval branch never calls `set-budget`, so `budget` stays null and `count` never reports an overrun | high | adopt | add `run.py approve RUN --budget N`; `assign` refuses when unapproved or over budget (reserve included) |
| A2 | No script fills a candidate's `source_digests`; the one path where the parent edits JSON by hand | high | adopt | add `findings.py digest <record.json> --target` (fills the trace and evidence files, writes back); SKILL.md only calls it |
| A3 | The launch of sub-agents does not name a read-only tool set; a general-purpose agent has Bash and can run the target's `make test` | high | adopt + defer | SKILL.md launch step: Read / Glob / Grep only, no type with Bash or Write. Bundling a sub-agent definition waits until the Skill mechanism is confirmed (defer) |
| A4 | `set-status complete` ignores leftover planned / in_progress units and pending candidates | medium | adopt | refuse while any remain |
| A5 | Agent ids can be reused within a run (`assign` checks only the unit's attempts) | low | adopt | collect used ids across the ledger and refuse |
| A6 | `count --n` writes a negative value unvalidated; `init --budget 0` leaves an empty directory | low | adopt | validate before writing; validate before mkdir |
| A7 | A log of a command that never ran or timed out still backs `existing_test` (only existence is checked) | medium | adopt | `record_errors` reads the log header (exit_code / timed_out) and refuses a log of a command that did not run; SKILL.md Phase 1 says what to do on failure |

## B. Nobody checks findings against the ledger

| # | Finding | Severity | Decision | Fix |
|---|---------|----------|----------|-----|
| B1 | A record never decided, or citing non-existent coverage ids, passes `add`, both validators stay green, and the report shows it as confirmed (reproduced) | high | adopt | `add` requires the fingerprint to be pending (decided for `--replace`) and the coverage ids to exist; `validate` cross-checks findings ⇄ decided ⇄ decisions; `compile.py` lists only decided records |
| B2 | A carried record whose unit is `deferred`, or whose coverage id does not resolve (quick → standard), ends up added but undecidable | high | adopt | `seed` keeps unresolved records out of `carried` and reports them as `unlinked_prior`; `decide --agent` also accepts a deferred unit (the verifier becomes its owner) |
| B3 | `--replace` silently adds a record whose fingerprint is not registered | medium | adopt | refuse when nothing is replaced |
| B4 | A replacement may change `coverage_ids` unchecked | medium | adopt | require fingerprint and coverage ids unchanged |
| B5 | A forgotten `decide` after a verdict-changing replacement is not caught | medium | adopt | caught by B1's cross-check |

## C. Places compared by name (the skill violates its own knowledge lesson)

| # | Finding | Severity | Decision | Fix |
|---|---------|----------|----------|-----|
| C1 | `is_inside` is bypassed by another case or NFD spelling, and the output directory is created inside the target (reproduced) | high | adopt | compare by stat identity (dev, ino), walking ancestors |
| C2 | `digests_for` follows symlinks inside the target to read and walk outside it, with no bound | medium | adopt | lstat; a symlink is "missing"; excluded from rglob; byte and file limits |
| C3 | A `.git` file's `gitdir:` may point anywhere; another repository's name and HEAD land in the artifacts | low-medium | adopt | gitdir must be under the target or a worktree layout; otherwise `unversioned` |
| C4 | `--prior` records are trusted unvalidated (absolute-path keys get digested; a broken record raises) | low-medium | adopt | pass prior records through `record_errors`; drop failures with a warning |
| C5 | `__pycache__` enters a directory digest, so `changed_source` can be misreported after `exec` | low | adopt | exclude `__pycache__` / `*.pyc` / `.git` from directory digests |

## D. Third-party text not made inert at the egress

| # | Finding | Severity | Decision | Fix |
|---|---------|----------|----------|-----|
| D1 | `plain()` passes C0 / C1 / bidirectional controls; a value inside backticks can break out | medium | adopt | strip Unicode category C; refuse backticks in values placed inside backticks |
| D2 | `$` anchors accept a trailing newline; fingerprints, agent ids and check logs duplicate | medium | adopt | `re.fullmatch` |
| D3 | The repo name from the target's remote URL is unbounded (ESC, spaces, `..`) and becomes the title and default directory name | medium | adopt | accept components by shape `^[A-Za-z0-9._-]{1,100}$`, else the basename |
| D4 | `exec` stores stdout / stderr raw in the log | low | document | verbatim to a file is the recorded practice; README warns not to `cat` the logs |

## E. Holes in the ledger state machine

| # | Finding | Severity | Decision | Fix |
|---|---------|----------|----------|-----|
| E1 | A critic reassigning a `candidate` unit makes `merge-critic` fail as a whole (candidates left unlinked) | medium | adopt | refuse reassigning a unit with candidates and say so in the critic contract: re-cut the surface via `missing_units` instead |
| E2 | A `blocked` unit's only exit is the critic | low | adopt | `defer` accepts blocked units (with a reason); SKILL.md covers blocked |
| E3 | A candidate carrying a `verdict` key silently overrides `proposed_verdict` | low | adopt | refuse both; name `proposed_verdict` in the contract |
| E4 | `seed` / `merge-critic` do not check that a class reference exists (SKILL.md claims "bad references" are refused) | medium | adopt | `build_unit` checks against the headings in `classes/` |
| E5 | Suppression of prior rejected claims is not enforced by `record` | medium | adopt | `record` does not queue a candidate matching `suppressed`; it notes it on the unit |
| E6 | A candidate's coverage ids need not include the unit that claimed it | low | adopt | require it |
| E7 | `status` gives only a count of `uncovered`; the critic needs the entries | medium | adopt | return them |

## F. SKILL.md gaps where the parent would stop

Adopt: F1 announce the four reconnaissance launches beforehand / F2 list the
required fields in the hunter and verifier contracts and hand over the path
of `SKILL_DIR/schema.json` (the shape of a rejected record, dropping
`agent_id`, `claimed_root_cause`) / F3 wrap target-derived text (log bodies,
record bodies) in nonce tags / F4 meanings of all 11 `prior_status` values and
how to pass prior findings / F5 `--knowledge` runs `classes.py check-knowledge`
in Phase 0 / F6 replace "TARGET is never written to" with "the parent never
writes; allowed commands' writes are listed in `writes`" / F7 mkdir
`RUN/agents/`; `note` only once RUN exists / F8 defer planned units left after
an abandon in quick; `incomplete` vocabulary for Phase 5; no third verifier for
one candidate / F9 architecture.md quotes no instruction-like text, only
`file:line` / F10 give the critic `unresolved` and the uncovered entries, and
say `already_present` may be ignored / F11 guidance on the number of units,
the choice of `selected_classes` and the shape of `excluded_classes` / F12 a
dirty target undermines carry-over / F13 the RUN files are the truth after a
history compaction.

## G. Hunting-class content

| # | Finding | Decision | Fix |
|---|---------|----------|-----|
| G1 | The second sentence of generic#Cryptography and secrets (weak primitives, timing, randomness) has no source; five sources are used but uncited | adopt | drop the unsourced sentence; complete the Source lines |
| G2 | Covered bars narrower, weaker or opposite to the source: Path confinement (three remedies, not "follows no link"), Places compared by name (identity **and** folded name), Credential follows a redirect (custom headers are not stripped), Lenient parsers (lenient reading is the remedy for MIME) | adopt | rewrite to the source |
| G3 | The server-side remedy in mcp#Server-authored text treated as fact is in no source (it came from the RFP table) | adopt | narrow to what the sources record (a proxy or aggregator passing other servers' descriptions through; third-party text in results without a mark); fix the RFP table |
| G4 | mcp#Third-party text reaches a terminal or log raw duplicates the cli class | adopt | delete the mcp copy (cli.md already covers a server's CLI face) |
| G5 | agent#Right operation, wrong value can never be covered | adopt | per the source: covered when the design document names the operational control (diff review), otherwise a hardening note |
| G6 | agent#Forbidden tool refused instead of absent: the source itself says it is not confinement | adopt | say it is hardening |
| G7 | Generic and product-type classes cite the same sources, so one check becomes two units | adopt | SKILL.md Phase 1: a generic class refined by a product-type class goes to `excluded_classes` with reason `refined by …` |
| G8 | Bars that reading cannot settle (whether a cage is effective, DNS rebinding, work_dir behaviour at runtime) | adopt | one line per class: `needs_validation` when reading cannot settle it |
| G9 | Ten recorded lessons of the same kind are missing | defer | three are adopted as added sources in G1; new classes wait for Phase 2 (agent-runtime.md has 283 bytes left; no padding). "A loosening setting readable from a caller-supplied file" is the strongest candidate |
| G10 | Seven smaller points (missing exceptions: machine-generated data is decoded leniently, marker files land by temp+rename, a preconfigured policy is not self-approval, …) | adopt | one line each in the class |

## H. Documents

| # | Finding | Decision | Fix |
|---|---------|----------|-----|
| H1 | RFP §2 tables lack `abandon`, `replacements.json`, `proposals.json`, `agents/`; §4 still says `carry` | adopt | update |
| H2 | Unrecorded residuals: `run.py exec` does not isolate the filesystem (the target's tests can write the run dir, HOME, the skill's own scripts); "the verifier never saw the hunter's prompt" cannot be closed by a script; an `env_allow` name denylist does not close | document | RFP §3 residual risks and README |

## I. Tests

18 of 21 mutations go unpinned (exec cwd escape, candidate linkage, duplicate
fingerprints, control characters in canonical refs, `|` in `plain()`,
repo-relative `writes`, reassign state limits, decisions ⊆ result
fingerprints, absolute-path refusal, minLength strip, check_log existence,
non-empty source_digests, blocked rules, ledger sort, reviewed_paths = union of
checks, ```` fence splitting, …). Adopt: a test per fix in A–E and a pin for
each of the 18.

## Rejected

- Adding ten new classes at once (G9): size and the RFP's no-padding rule;
  recorded as Phase 2 candidates.
- Bundling a sub-agent definition file (second half of A3): after confirming
  that a Skill can ship agents; the SKILL.md launch spec covers it for now.
- Raw exec logs (D4): verbatim to a file is the recorded practice.

## Order of application (by risk)

C1 → B1 / B2 → A1 / A2 / A3 / A7 → D1–D3 → E → F → G → H → I.

---

# Round two (2026-11-08, over the cut-4 fixes `26fdbc4..e0a7f61`)

Two verifiers (scripts: re-run the round-one reproductions and look for
bypasses next to each fix / SKILL.md, classes and documents). Every adopted
round-one item was confirmed refused or correct. Below are only the new
findings. The weight dropped (one high, and it is a text issue), so the
adopted items are fixed in cut (5) and the verification rounds stop there;
E2E follows (risk assessment over perfection).

## S. Scripts (next to the fixes)

| # | Finding | Severity | Decision | Fix |
|---|---------|----------|----------|-----|
| S1 | `set-budget` after `approve` raises the budget and keeps the approval | medium | adopt | refuse `set-budget` once approved; raising goes through `approve --budget` |
| S2 | `assign`'s "spent" is the parent's own `count`; without `count` calls the budget is bypassed | medium | adopt | `assign` counts the hunter invocation itself (SKILL.md's `count hunter` only for re-runs) |
| S3 | The reserve shrinks as planned units decrease, so more hunters pass than estimated | medium-low | adopt | `expected_candidates` from planned + in_progress |
| S4 | `add` checks only that coverage ids exist; a record not linked to the claiming unit passes both validators and reaches the report | medium | adopt | first add requires the queued candidate's coverage ids; `cross_check` requires coverage ids ⊆ units that hold the fingerprint |
| S5 | `missing` / `symlink` / `too-large` enter source_digests and compare equal as "unchanged"; a confirmed citing a non-existent file reaches the report (reproduced) | medium | adopt | records and units accept only 64-hex digests; `digests_unchanged` is False with any non-hex value |
| S6 | A newline in `commands.json` `source` forges the log header; a timed-out log passes as evidence | medium-low | adopt | no newlines in command-ledger strings; the header takes the first occurrence |
| S7 | After reassigning a unit whose fingerprints were decided, a verdict-changing replacement cannot be re-decided and `complete` still passes | medium-low | adopt | re-decision also updates archived attempts' decisions; `set-status complete` runs validate and cross_check |
| S8 | Critic, reconnaissance and non-`decide` verifier ids never enter the ledger; reuse across roles is not caught | low-medium | adopt | `used_agent_ids` also collects candidates / notes / replacements; `merge-critic` records the critic id |
| S9 | No size limit on a directly cited file (a 3 GiB sparse file is read whole) | low | adopt | byte limit for regular files too |
| S10 | stderr reflects offending values raw (controls to the parent's terminal) | low | adopt | `die` / `fail_if` strip control characters |
| S11 | The same `--prior` twice duplicates carried / suppressed | low | adopt | deduplicate by realpath |
| S12 | One fingerprint both carried (later needs_validation) and suppressed (earlier rejected) | low | adopt | a carried fingerprint leaves suppressed |
| S13 | The unversioned branch's repo name skips the shape rule | low | adopt | same reduction |
| S14 | The `commondir` predicate accepts any ancestor | low | adopt | require `gitdir == common/worktrees/<name>` |
| S15 | An output path through a link inside the target is outside by identity, inside by name | low | adopt | refuse when an ancestor of the output's absolute path is inside the target by name |
| S16 | `init --output <existing file>` raises | low | adopt | check `is_dir` and die |
| S17 | `decide --agent` turns an unhunted unit into `candidate` with a synthetic check | low | defer | the re-check of a carried record is read as that unit's evidence; noted in AGENTS |
| S18 | `complete` passes with blocked units left | low | adopt | refuse blocked too (defer or reassign them) |
| S19 | Eight unpinned checks (agent ids in checks, could-not-start logs, two cross_check rules, `approve --budget 0`, controls in dict keys, complete with only pending candidates, same-owner attempts) | — | adopt | pins |

## T. SKILL.md, classes, documents

| # | Finding | Severity | Decision | Fix |
|---|---------|----------|----------|-----|
| T1 | One sentence in generic.md is identical to the origin and seven are close paraphrases; LICENSE / README say no verbatim text is included | high | adopt | rewrite the identical sentence; change order and structure of the close ones |
| T2 | mcp#Server-authored text's "do not rewrite MCP result data" is in no cited heading | medium | adopt | cite its source (security.md "Making text inert at the ingress …") |
| T3 | `run.py count` sits after a successful apply, so discarded returns are not counted | medium | adopt | count per launch, before applying (as Phase 5 does) |
| T4 | The re-verifier prompt lacks `<target-data>` and exit_code; critic inputs (unresolved, uncovered reasons) are target-derived too | medium | adopt | the Phase 4 sentence in Phase 5 and the critic |
| T5 | "Refines generic X" is free prose; the parent cannot build excluded_classes mechanically, and excluding the generic class drops the origin lens | medium | adopt | a `Refines:` line beside `Source:`, printed by `classes.py list` and checked; exclusion only when the generic class's remaining lessons do not apply to the surface |
| T6 | `fingerprint` missing from the hunter contract list / `prior_blocked` meaning / `--prior` order / destination of changed-source prior records / complete with budget-deferred units / `checks_unavailable` trigger / notes on keep / `carried_from` kept / agents/ "as received" | low | adopt | one clause each; changed-source prior records reported as `changed_prior` |
| T7 | cli#Absolute paths refines the wrong generic class / the MIME remedy missing from the Parsers bar / needs_validation vs blocked in G8 / dispositions for Right operation and Forbidden tool | low | adopt | one clause each |
| T8 | 8 KB and two source kinds left in AGENTS; 8 KB and "either … or" left in the RFP; "fourteen" (F has 13 plus A3 and G7) | low | adopt | align |
| T9 | mcp and agent-runtime Server-authored text classes share sources (double unit for a proxy that is also a runtime) | low | defer | product-to-product overlap is outside the rule; Phase 2 |
