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
  check-knowledge). 39 tests over a fixture repository with a deliberate
  path traversal.

### Planned for 0.1.0

Phase 1 cuts (2) and (3): the generic and three organization hunting-class
files, and the full six-phase SKILL.md with `quick` / `standard` profiles,
the cost gate and `--prior` carry-over.
