# Changelog

## [0.2.0] - 2026-11-09

Cut (10): lessons E37–E40 of the first production run (gem-agent, standard,
no prior; `docs/{ja,en}/reviews/2026-11-09-standard-gem-agent*.md`).

### Added

- **`findings.py accept`** (E39): the owner's triage logged in the run —
  `--fingerprint`, `--record` (the ADR or document that keeps the
  behaviour), `--reason`, optional `--date`, `--withdraw` to reverse — in
  `dispositions.json` (append-only, latest entry wins). `compile.py` prints
  the disposition under the finding; `seed --prior` lists an accepted record
  as `accepted_prior` and marks its units `prior_accepted_same_source` /
  `prior_accepted_changed_source`; with unchanged sources it is neither
  carried for re-verification nor reported again (`ledger.py record`
  suppresses the same claim), with changed sources the unit is hunted with
  the acceptance as its pointer. Prior dispositions are validated like every
  other prior input and dropped with a warning when they do not validate.
- **Rule 3 of `references/severity.md`** (E37): a new confirmed record
  answers `path_actor` (`unasked` / `operator_composed`) and `specified_in`
  (the record that decided the behaviour, or `none`). An operator-composed
  path whose behaviour a record decided is not a finding: `findings.py add`
  refuses the confirmed form, the verifier returns `rejected` naming the
  record, and a new note kind **`documentation`** holds the gap in what the
  operator reads. The schema keeps both fields optional so prior runs'
  records still load; the briefs' `required_fields` list them; the report
  prints them under each finding.
- Hunting classes (E40): `agent-runtime.md` gains "Approval dialog shows
  less than the call" and "Lane-writable directory reused on resume"; the
  toolchain-cache class cites the measured remedy (what an approved build
  trusts sits outside every allow; a denial by name is a second line);
  `generic.md`'s resource class cites the x/net/html quadratic allocation.
  54 classes, 119 citations.

### Changed

- **Estimate** (E38): the candidate rate follows whether the unit has a
  prior, not the profile (`fresh` 0.60, `prior` 0.30; the first production
  run measured over 0.75 on 71 fresh units against a constant of 0.30 and
  ran out of budget). `estimate` returns `fresh_units`, `prior_units`,
  `candidates_per_unit` as a table and `shortfall`; SKILL.md says at the
  cost gate that a lower budget ends the run incomplete. A unit a prior run
  deferred or set aside counts as fresh (review).

### Fixed

- Commit-time review of cut 10 (record in the review document): a prior
  run's dispositions, lead notes and records are dropped when they spell the
  operator's login or an absolute local path; with several priors one
  fingerprint sits in one bucket only, the latest prior's; a broken
  `dispositions.json` of the run itself stops the scripts instead of
  crashing `compile.py`; `findings.py validate` re-checks rule 3 on records
  that carry the new fields; the acceptance date must be a calendar date;
  `ledger.py status` prints `accepted_prior`.

## [0.1.0] - 2026-11-09

First release: the full six-phase audit for both profiles, after Phase 3's
four end-to-end runs and nine cuts of lessons.

### Added

- Repository scaffold (ADR-004 layout): placeholder `code-audit/SKILL.md`
  that authorizes guidance mode only, vendored `tests/validate-skill.sh`,
  `tests/run-script-tests.py` with the distribution-boundary invariants
  (stdlib-only scripts, no absolute local paths, frontmatter name), Makefile,
  bilingual READMEs, CLAUDE.md, AGENTS.md.
- RFP (`docs/ja/code-audit-rfp.ja.md`, English mirror in `docs/en/`), Draft
  of 2026-11-08, including the design-freeze independent verification pass.

- Phase 1 cut (1) — contracts and bookkeeping scripts (stdlib-only Python):
  `schema.json` (run metadata, command ledger, ledger unit, hunter and
  critic results, the three findings branches, notes),
  `references/severity.md` (vocabulary; rule 1 overall ≤ impact, rule 2
  source-only evidence caps confidence at medium), `scripts/_contract.py`
  (schema-subset validator, path and id rules, `coverage_id` derivation,
  source digests), `scripts/run.py` (init with resolved-path refusal of an
  output inside the target, budget and invocation counters, bounded `exec`
  of ledger-allowed commands from an empty environment with a time limit),
  `scripts/ledger.py` (seed with prior-run carry-over and suppression,
  assign, record applied whole-or-nothing, merge-critic with attempt
  archiving and quick-profile deferral, decide, defer, estimate, validate,
  status), `scripts/findings.py` (validate, add one record at a time with
  stale-digest refusal, note), `scripts/compile.py` (ja/en reports derived
  from records, code only inside fences), `scripts/classes.py` (list, size,
  check-knowledge). Tests run over a fixture repository with a deliberate
  path traversal.
- Hardening from the commit-time security review: `run.py init` never lets
  the target's `.git/config` reach git — it builds a scratch git-dir (HEAD,
  index, refs, exclude data copied; objects linked; a config of its own with
  data keys only) and runs git against that with `-c` overrides and a
  minimal environment, because a repository-defined clean filter runs under
  `git status` and cannot be undefined from the command line; the copy into
  the scratch git-dir follows no symlink, takes regular files only and stops
  at a byte and file budget; `run.py exec` runs the command in its own
  session and kills the whole process group on timeout.
- Phase 1 cut (2) — hunting classes and the workflow: `classes/generic.md`
  (nine generic classes) and `classes/mcp-server.md`, `classes/cli.md`,
  `classes/agent-runtime.md` (52 classes in all), every class citing the
  knowledge heading or ADR where the organization recorded the lesson
  (verified against the checkouts with `classes.py check-knowledge`); the
  six-phase `SKILL.md` — security preamble, guidance vs full audit with one
  question when ambiguous, four-role reconnaissance that also writes the
  command ledger and runs the allowed tests once, the human cost gate, the
  hunter / critic / verifier prompts with their output contracts and
  negative space, the verifier's reconstruction of preventing layers, and the
  report step — complete for `quick`, with the `standard`-only sections
  marked for cut (3). `ledger.py abandon` returns a discarded hunter's units
  to `planned` with the attempt archived; `compile.py` lists candidates that
  were never decided, without a verdict; `classes.py` keeps commas inside a
  cited heading.
- Phase 1 cut (3) — the `standard` profile and carry-over in SKILL.md: hunting
  waves that repeat while the critic reports work remaining (fresh hunters
  for reassigned units), the independent re-verification stage with its
  prompt and the replacement rule, and `--prior` wiring (prior status in the
  hunter prompt, carried records verified first, suppressed claims and
  resolved prior leads given to the critic). `findings.py add --replace` now
  takes `--by` and enforces the rule: a replacement that strengthens the
  verdict, severity, confidence or evidence kind is refused until
  `--confirmed-by` names a different fresh verifier; every replacement is
  logged in `replacements.json` and counted in the report. `ledger.py decide`
  accepts a re-decision after a verdict-changing replacement.
- Pre-release independent verification (first round, 2026-11-08; triage in
  `docs/{ja,en}/reviews/2026-11-08-pre-release-verification*.md`) and cut
  (4), its adopted findings: places compared by identity, link-free bounded
  digests, foreign git-dirs refused, prior runs validated; findings bound to
  the ledger with a cross-check in both validators and decided-only reports;
  the cost gate, agent freshness and evidence-log validity enforced by the
  scripts (`run.py approve`, `run.py nonce`, `findings.py digest`); report
  text made inert and identifiers matched whole; the ledger state-machine
  holes closed (pending-candidate reassignment, blocked units, class
  references, suppressed claims, candidate coverage ids); SKILL.md completed
  on the thirteen points the parent would have stopped at (plus the sub-agent launch rule and the generic-class exclusion); the hunting
  classes rewritten to their sources, with `origin:` as a third source kind
  (user decision 2026-11-08: borrow the origin skill's generic lenses in our
  own words where the organization has little recorded knowledge); pins for
  the eighteen controls the mutation review found unpinned.
- Second independent verification round (over the cut-4 fixes) and cut (5),
  its adopted findings: the budget changes only through `approve`; `assign`
  counts the hunter and the reserve counts in-progress units; a record keeps
  the queued candidate's coverage ids and the cross-check requires each to
  have claimed the fingerprint; only real digests count (a missing, linked or
  oversized file is refused, two markers never compare unchanged); no line
  breaks in the command ledger and the log header takes its first values; a
  re-decision reaches archived attempts; `set-status complete` runs both
  validators and refuses blocked and budget-deferred units; used agent ids
  come from the whole run (`count --agent`, critics, notes, replacements);
  priors deduplicated, read oldest first, a carried claim leaves suppressed,
  changed-source prior records reported; stderr made inert; the unversioned
  name, the commondir predicate, an output inside the target by name and an
  existing-file output handled. Classes: `Refines:` lines the scripts read
  replace the prose, generic.md carries no sentence of the origin verbatim,
  the one unsourced sentence cites its heading, bars and dispositions
  settled. SKILL.md counts every launch when it happens and wraps every
  target-derived input. 89 tests.
- First end-to-end run (2026-11-08, `webhook-relay`, quick: 29 launches,
  about 2.6M tokens, 5 confirmed / 2 needs_validation / 7 rejected; record
  in `docs/{ja,en}/reviews/2026-11-08-e2e-smoke-webhook-relay*.md`) and cut
  (6), its lessons: `run.py count --agent` refuses a counted id without
  `--rerun`; `record` keeps the union of the checks' paths and refuses only a
  missing one; a fingerprint may lead with a dot; the estimate groups units
  per hunter, expects one candidate per two units and budgets re-asks;
  `run.py exec` redirects `GOCACHE`, `XDG_CACHE_HOME` and
  `PYTHONPYCACHEPREFIX` under `RUN/cache/` with `GOPROXY=off`,
  `GOFLAGS=-mod=readonly`, `GOTOOLCHAIN=local`; `ledger.py merge-candidates`
  folds duplicate claims before verification and the report lists them;
  `ledger.py brief critic|verifier` prints the sub-agent's input from the
  books; `lead` notes are carried to the next run's critic by `seed --prior`;
  the coverage line counts decided candidate units; SKILL.md states the
  one-sink trace shape, repository-relative reconnaissance paths, the merge
  step, the briefs and schema parts by reference; the two leftover "Refines
  generic" sentences in `cli.md` removed. 92 tests.

- Second end-to-end run (2026-11-08, `webhook-relay`, standard with `--prior`:
  42 launches, about 3.9M tokens, 0 confirmed / 2 needs_validation / 7
  rejected; record in `docs/{ja,en}/reviews/2026-11-08-e2e-standard-webhook-relay*.md`)
  and cut (7), its lessons: `seed --prior` matches prior units by
  surface × boundary × class when the coverage id's subsystem token differs
  (a quick prior under standard carried over instead of `unlinked_prior`;
  carried records take this run's ids, listed as `remapped_prior`); a unit
  the critic adds to a run with priors is `new`; `ledger.py brief` gains the
  `hunter` (assigned units with verbatim class text) and `reverifier`
  (decided record, units, logs) roles; the estimate assumes 0.35 candidates
  per unit and 10% re-asks; the report's replacement line no longer claims a
  second verifier when nothing was strengthened; SKILL.md names the briefs
  for every role, states the critic's types, and allows verification between
  waves. Deferred: E20 (a `brief critic --since-wave` delta). 94 tests.
- Third end-to-end run (2026-11-08, `web-fetch`, quick: 43 launches, about
  4.6M tokens, 6 confirmed / 1 needs_validation / 9 rejected; record in
  `docs/{ja,en}/reviews/2026-11-08-e2e-quick-web-fetch*.md`) and cut (8),
  its lessons: `ledger.py architecture` composes `architecture.md` from the
  saved reconnaissance returns and every `brief` requires it; the critic's
  and verifier's briefs carry the candidate's proposed verdict and root
  cause, and the verifier's the required fields per verdict and the file
  rule; invalid JSON is refused with its position and context; the estimate
  subtracts launched critics, uses the real queue once hunting is over and
  takes per-profile candidate rates (quick 0.45 / standard 0.30) with 15%
  re-asks; SKILL.md keeps whole-tree units alone with their hunter, passes
  the cost gate again only on a shortfall the books show, and lets verifiers
  read pinned dependencies and GOROOT, cited in prose. 97 tests.
- Fourth end-to-end run (2026-11-08, `web-fetch`, standard with `--prior`:
  56 launches, about 6.2M tokens, on the estimate; 6 confirmed / 0
  needs_validation / 6 rejected, 2 of 12 records replaced on re-verification
  without strengthening; record in
  `docs/{ja,en}/reviews/2026-11-08-e2e-standard-web-fetch*.md`). Lessons
  E29–E36 recorded as candidates for cut 9: the nonce on the closing wrapper
  tag; `prior_needs_validation_changed_source`; trace and evidence required
  fields in the verifier's brief; personal identifiers and local paths never
  spelled in a return, refused by the scripts; re-verifiers in the estimate;
  a file listing in the hunter's brief; the report's replacement line by
  kind of difference.
- Cut (9), the fourth run's adopted lessons (E29–E35; E36 waits for more
  measurements): `run.py nonce` prints both wrapper tags and SKILL.md puts
  the nonce on the closing tag too (`<target-data-N>…</target-data-N>`);
  `seed --prior` marks a needs_validation lead whose source changed as
  `prior_needs_validation_changed_source`; the verifier's and re-verifier's
  briefs list the required fields of `trace_entry` and `evidence_entry`;
  `record`, `merge-critic`, `architecture`, `findings.py add` and `note`
  refuse a return that spells the operator's login or an absolute local
  path (every role's contract says: describe, never spell); the estimate
  counts one re-verifier per decided record in `standard`;
  `brief hunter --target` lists the files under each unit's starting paths
  (capped, links unfollowed, `.git` skipped); the replacement log records
  the fields a replacement weakened and the report counts strengthening,
  weakening and wording replacements apart. Hardening from the commit-time
  review of the cut: the file listing refuses a starting path that is not
  repository-relative, has a link in any component or names a vendored
  tree, and prunes vendored and cache trees while walking; the local-path
  pattern takes repeated slashes, `/Volumes` and `/private/var/folders`; the
  login match is case-insensitive; the parent's own `--reason` texts and the
  unit proposals' prose pass the identifier check; a strengthening
  replacement that also weakens a field is said so in the report. 102 tests.

