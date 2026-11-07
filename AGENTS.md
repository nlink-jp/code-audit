# AGENTS.md — code-audit

## Project summary

Claude Code Skill for a repository-wide vulnerability audit of the
organization's own code (design: the RFP in `docs/`). The parent agent runs
six phases over isolated sub-agents — reconnaissance → coverage-led hunting
waves → adversarial candidate validation → schema-validated `findings.json`
(`confirmed` / `needs_validation` / `rejected`) → independent re-verification
→ Japanese/English report derived from the records — behind a deterministic
coverage ledger and a human-approved cost gate. Hunting classes come from the
organization's recorded defects (MCP servers, CLIs, LLM agent runtimes)
beside generic classes. Invoked as `/code-audit <target-dir> ...`.

**Status: Phase 1, cut (1) done.** The five bookkeeping scripts, the data
contracts and their tests exist. SKILL.md is still a placeholder that
authorizes guidance mode only; the six-phase workflow (cut 2) and the
standard-profile waves and carry-over wiring in SKILL.md (cut 3) are next.

## Key commands

| Command | Purpose |
|---------|---------|
| `make check` (= `make test`) | Structural validation + script behaviour tests (39 tests) |
| `make install` | Build the zip and unpack it into `~/.claude/skills/code-audit` |
| `make install DEST=<path>` | Unpack into a custom skills directory |
| `make uninstall` | Remove the installed copy |
| `make package` | Build `dist/code-audit-vX.Y.Z.zip` (zip root = skill folder) |
| `make clean` | Remove `dist/` |

Bundled scripts (stdlib-only Python 3.9+; `--help` on each):

| Script | Subcommands | Owns |
|--------|-------------|------|
| `run.py` | `init`, `set-budget`, `count`, `set-status`, `validate`, `exec` | `run-metadata.json`, `checks/<id>.log` |
| `ledger.py` | `seed [--prior]`, `assign`, `record`, `merge-critic`, `decide`, `defer`, `estimate`, `validate`, `status` | `coverage-ledger.json`, `candidates.json` (and appends hunter notes to `notes.json`) |
| `findings.py` | `validate`, `add [--replace]`, `note` | `findings.json`, `notes.json` |
| `compile.py` | (run dir) | `REPORT.ja.md`, `REPORT.md`, `NEEDS-VALIDATION.ja.md`, `NEEDS-VALIDATION.md` |
| `classes.py` | `list`, `size`, `check-knowledge [--adr]` | nothing; checks `classes/*.md` |

## Directory structure

```
code-audit/
├── code-audit/              The skill — the only thing that ships
│   ├── SKILL.md             Placeholder (guidance mode only) until cut 2
│   ├── schema.json          Parts: metadata, commands, unit_proposal, check, unit, hunter_result,
│   │                        critic_result, trace_entry, evidence_entry, finding_{confirmed,
│   │                        needs_validation,rejected}, note
│   ├── references/
│   │   └── severity.md      Likelihood / impact / overall / confidence vocabulary, rules 1 and 2
│   └── scripts/             stdlib-only Python 3.9+
│       ├── _contract.py     Schema-subset validator, JSON I/O, path and id rules, coverage_id, digests
│       ├── run.py           Run metadata, budget/invocation counters, bounded `exec`
│       ├── ledger.py        Coverage ledger state machine, candidates queue, estimate
│       ├── findings.py      Findings records (one at a time), notes
│       ├── compile.py       Reports derived from records; code only inside fences
│       └── classes.py       Hunting-class parser, size and source checks
├── tests/
│   ├── validate-skill.sh    Frontmatter + link structure checks (vendored, ADR-006)
│   ├── run-script-tests.py  unittest suite: boundary invariants + full flows over the fixtures
│   └── fixtures/
│       ├── sample-repo/     Tiny Python app with a deliberate path traversal + its own test + Makefile
│       ├── units.json       Two unit proposals; hunter-result.json / critic-result.json / record-rejected.json
│       ├── commands.json    Allowed, forbidden, env-probe and timeout entries
│       ├── classes/         A class file citing a knowledge heading and an ADR
│       ├── knowledge/       Minimal knowledge tree (docs/en/security.md) for check-knowledge
│       └── adr/             One ADR file for the --adr check
├── docs/
│   ├── ja/code-audit-rfp.ja.md   RFP (primary)
│   └── en/code-audit-rfp.md      RFP (English mirror)
├── Makefile
├── README.md / README.ja.md
├── CHANGELOG.md
├── CLAUDE.md / AGENTS.md
└── LICENSE
```

## Run directory layout (what the scripts produce)

| File | Written by | Content |
|------|-----------|---------|
| `run-metadata.json` | `run.py` | run_id, repo name (git remote, never a path), source ref + dirty, profile, budget, invocation counters, run_status + reason |
| `commands.json` | the parent, during reconnaissance | the target's test/check commands, each allowed or forbidden with a reason, `env_allow`, `timeout_sec`, `writes`, `source` |
| `checks/<id>.log` | `run.py exec` | command, allowed variable names, exit code, duration, stdout/stderr |
| `coverage-ledger.json` | `ledger.py` | units: canonical refs → `coverage_id`, starting paths + `source_digests`, prior_status, state, owner, checks, fingerprints, decisions, archived `attempts` |
| `candidates.json` | `ledger.py` | `candidates` (hunter-proposed, pending), `carried` (from prior runs), `decided`, `suppressed` (prior rejected, same source), `uncovered`, `resolved_prior_leads` |
| `findings.json` | `findings.py` | decided records, sorted by fingerprint |
| `notes.json` | `ledger.py record` / `findings.py note` | hardening and out-of-scope notes with the author's agent id |
| `architecture.md` | the parent | reconnaissance summary |
| `REPORT*.md`, `NEEDS-VALIDATION*.md` | `compile.py` | derived reports |

## Gotchas

- The `code-audit/` subdirectory is the distribution boundary (ADR-004):
  `make package` zips exactly that directory. Never add repo-level files
  inside it.
- The directory name is the slash command; frontmatter `name` must match
  it, and `description` must stay at or under 1,024 characters. `make
  check` enforces both.
- **Scripts must stay stdlib-only** — `run-script-tests.py` scans every
  bundled script's imports against `sys.stdlib_module_names` (siblings in
  `scripts/` are allowed; `findings.py` imports `ledger` for the one
  definition of a record's bar, `record_errors`).
- **`coverage_id` is derived only in `_contract.py`** and called only from
  `ledger.py`; a test pins this. Percent-encode the NFC canonical refs and
  join with `::`; the quick profile substitutes
  `profile/quick/all-in-scope-subsystems` for the subsystem.
- **State table** (`ledger.py validate`): planned → unassigned, empty;
  deferred / out_of_scope / not_applicable → unassigned, reason in
  `unresolved`; in_progress → owner, empty; blocked → owner, evidence,
  unresolved, no fingerprints; covered → owner, evidence, nothing else;
  candidate → owner, evidence, fingerprints. A reassigned unit archives its
  attempt and needs a fresh owner.
- **A hunter result is applied whole or not at all**: every unit assigned to
  the agent appears exactly once, every claimed fingerprint has a candidate
  record that passes the findings bar, and unit `reviewed_paths` equal the
  union of its checks' paths.
- **`decide` requires the record first** (`findings.py add`), then links the
  fingerprint to units; a carried record on a still-planned unit needs
  `--agent` (the verifier becomes the owner).
- **Prior-run precedence** when seeding with `--prior`: a record-derived
  status outranks a unit-derived one; among records, confirmed (changed >
  same) > needs_validation > rejected-claim-changed. Same-source confirmed
  and needs_validation records are carried into `candidates.carried`;
  same-source rejected ones go to `suppressed`.
- **Nothing that ships or is produced may carry an absolute local path** —
  `run-script-tests.py` greps the skill directory; `run.py init` records
  the repo name from the git remote and prior runs by basename.
- **Execution boundary (RFP §3):** sub-agents read and return JSON. The
  parent alone runs the target's existing tests via `run.py exec`, from an
  empty environment plus allowlisted variables (`PATH` always), with a time
  limit, and only for commands `commands.json` allows. `exec` cannot block
  the network; a command that reaches it is forbidden in the ledger instead.
  macOS Python adds `LC_CTYPE` / `__CF_USER_TEXT_ENCODING` inside the child
  on its own; the test checks that a sentinel variable does not leak rather
  than an exact set.
- **Evidence kinds:** `source` or `existing_test` (a `checks/` log).
  `findings.py validate` enforces rule 1 (overall ≤ impact) and rule 2
  (source-only ⇒ confidence ≤ medium) from `references/severity.md`; the
  report shows the evidence kind beside every confirmed finding. This is a
  user decision recorded in the RFP; do not re-open it.
- **`compile.py` escapes prose** (collapses lines, breaks ``` and `|`) and
  puts code only inside four-backtick fences; a test walks the report and
  asserts every `fixed_code` line sits inside a fence.
- **Default output is `~/code-audit-runs/<repo>/run-<N>`**; a directory inside
  the target (or containing it) is refused by resolved-path comparison before
  the emptiness check.
- `tests/validate-skill.sh` is a byte-identical vendored copy of
  `.github/templates/validate-skill.sh` (ADR-006) — never edit it here.
- After `make install` for verification, remove the copy from
  `~/.claude/skills/` before ending the session; the app registration is the
  normal install route and a leftover copy registers the skill twice.
- Releases follow the org checklist with `make package` in place of a
  binary build; before uploading, unzip the artifact and confirm
  `code-audit/SKILL.md` sits directly under the zip root.

## Module path

Repository: `github.com/nlink-jp/code-audit`
