# Changelog

## [Unreleased]

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
  on the fourteen points the parent would have stopped at; the hunting
  classes rewritten to their sources, with `origin:` as a third source kind
  (user decision 2026-11-08: borrow the origin skill's generic lenses in our
  own words where the organization has little recorded knowledge). 71
  tests.

### Planned for 0.1.0

Phase 3: a second independent verification pass over the cut-4 fixes;
end-to-end runs on two organization repositories (one MCP server, one CLI)
with invocations, tokens and cost recorded against the estimate; release per
the organization checklist.
