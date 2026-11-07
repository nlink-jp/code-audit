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

### Planned for 0.1.0

Phase 1 of the RFP development plan: `schema.json`,
`references/severity.md`, the five stdlib scripts (`run.py`, `ledger.py`,
`findings.py`, `compile.py`, `classes.py`) with unittest coverage, the
generic and three organization hunting-class files, and the full six-phase
SKILL.md with `quick` / `standard` profiles, the cost gate and `--prior`
carry-over.
