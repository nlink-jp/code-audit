---
name: code-audit
description: Repository-wide vulnerability audit of your own code, run as isolated sub-agents behind a coverage ledger — reconnaissance, coverage-led hunting, adversarial validation by a fresh verifier, schema-validated findings (confirmed / needs_validation / rejected), independent re-verification, and a Japanese/English report derived from the records. Hunting classes come from the organization's own recorded defects (MCP servers, CLIs, LLM agent runtimes) beside the generic classes. Use for a full security audit or pen-test-style review of one repository, 脆弱性監査, リポジトリ全体のセキュリティ監査, 信頼境界のレビュー, コード監査; also answers security questions and focused reviews in guidance mode without producing artifacts. For reviewing a diff, use /security-review; for regulations vs an application, use compliance-review.
argument-hint: "<target-dir> [--output <dir>] [--profile quick|standard] [--budget <N>] [--prior <run-dir>]... [--knowledge <dir>]"
---

# code-audit — scaffold

This skill is scaffolded and not yet implemented. The design is fixed in the
RFP of this repository (`docs/ja/code-audit-rfp.ja.md`, English mirror in
`docs/en/code-audit-rfp.md`); Phase 1 of its development plan fills in the
files listed below.

Until then, loading this skill authorizes **guidance mode only**: answer
security questions and perform focused reviews from source reading. Do not
create an output directory, do not launch sub-agents for a full audit, and do
not present any reading-based conclusion as a verified finding.

## Planned layout

- `scripts/run.py`, `scripts/ledger.py`, `scripts/findings.py`,
  `scripts/compile.py`, `scripts/classes.py` — stdlib-only Python that keeps
  the books (run metadata, coverage ledger, findings records, reports,
  hunting-class sources). The model decides; the scripts record.
- `schema.json` — the data contract: three findings branches, ledger unit,
  run metadata, command ledger.
- `references/severity.md` — the five severity anchors and the high/medium
  discriminator that `findings.py validate` enforces.
- `classes/` — hunting classes: one generic file and one file per
  organization product type (MCP server, CLI, LLM agent runtime), each class
  citing its source in the organization's knowledge base or an ADR.
