---
name: code-audit
description: Repository-wide vulnerability audit of your own code, run as isolated sub-agents behind a coverage ledger — reconnaissance, coverage-led hunting, adversarial validation by a fresh verifier, schema-validated findings (confirmed / needs_validation / rejected), independent re-verification, and a Japanese/English report derived from the records. Hunting classes come from the organization's own recorded defects (MCP servers, CLIs, LLM agent runtimes) beside the generic classes. Use for a full security audit or pen-test-style review of one repository, 脆弱性監査, リポジトリ全体のセキュリティ監査, 信頼境界のレビュー, コード監査; also answers security questions and focused reviews in guidance mode without producing artifacts. For reviewing a diff, use /security-review; for regulations vs an application, use compliance-review.
argument-hint: "<target-dir> [--output <dir>] [--profile quick|standard] [--budget <N>] [--prior <run-dir>]... [--knowledge <dir>]"
---

# code-audit — under construction

The bookkeeping scripts and data contracts of this skill exist; the audit
workflow itself (the six phases and the hunting classes) is not written yet.
The design is fixed in the RFP of this repository
(`docs/ja/code-audit-rfp.ja.md`, English mirror in `docs/en/code-audit-rfp.md`).

Until the workflow lands, loading this skill authorizes **guidance mode
only**: answer security questions and perform focused reviews from source
reading. Do not create an output directory, do not launch sub-agents for a
full audit, and do not present any reading-based conclusion as a verified
finding.

## Layout

- `scripts/` — stdlib-only Python that keeps the books. The model decides;
  the scripts record. `run.py` owns run-metadata.json and bounded execution of
  the target's existing tests; `ledger.py` owns coverage-ledger.json and
  candidates.json; `findings.py` owns findings.json and notes.json;
  `compile.py` derives the reports; `classes.py` checks the hunting-class
  files against their sources.
- `schema.json` — the data contracts: run metadata, command ledger, ledger
  unit, hunter and critic results, the three findings branches, notes.
- `references/severity.md` — the severity and confidence vocabulary and the
  two rules `findings.py validate` enforces.
- `classes/` (pending) — hunting classes: one generic file and one file per
  organization product type (MCP server, CLI, LLM agent runtime), each class
  citing its source in the organization's knowledge base or an ADR.
