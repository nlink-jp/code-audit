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

**Status: scaffold.** The skill directory holds a placeholder SKILL.md that
authorizes guidance mode only. Phase 1 of the RFP's development plan fills in
the scripts, schema, classes and the full workflow.

## Key commands

| Command | Purpose |
|---------|---------|
| `make check` (= `make test`) | Structural validation + script behaviour tests |
| `make install` | Build the zip and unpack it into `~/.claude/skills/code-audit` |
| `make install DEST=<path>` | Unpack into a custom skills directory |
| `make uninstall` | Remove the installed copy |
| `make package` | Build `dist/code-audit-vX.Y.Z.zip` (zip root = skill folder) |
| `make clean` | Remove `dist/` |

## Directory structure

```
code-audit/
├── code-audit/              The skill — the only thing that ships
│   ├── SKILL.md             Frontmatter + (planned) adversarial-input preamble, modes, six phases
│   ├── schema.json          (planned) findings branches / ledger unit / run metadata / command ledger
│   ├── references/          (planned) severity.md — anchors and the high/medium discriminator
│   ├── classes/             (planned) generic.md, mcp-server.md, cli.md, agent-runtime.md
│   └── scripts/             (planned) stdlib-only Python 3.9+: run.py, ledger.py, findings.py, compile.py, classes.py
├── tests/
│   ├── validate-skill.sh    Frontmatter + link structure checks (vendored, ADR-006)
│   └── run-script-tests.py  unittest suite for the bundled scripts and boundary invariants
├── docs/
│   ├── ja/code-audit-rfp.ja.md   RFP (primary)
│   └── en/code-audit-rfp.md      RFP (English mirror)
├── Makefile
├── README.md / README.ja.md
├── CHANGELOG.md
├── CLAUDE.md / AGENTS.md
└── LICENSE
```

## Gotchas

- The `code-audit/` subdirectory is the distribution boundary (ADR-004):
  `make package` zips exactly that directory. Never add repo-level files
  inside it.
- The directory name is the slash command; frontmatter `name` must match
  it, and `description` must stay at or under 1,024 characters. `make
  check` enforces both.
- **Scripts must stay stdlib-only** — `run-script-tests.py` scans every
  bundled script's imports against `sys.stdlib_module_names`.
- **Nothing that ships or is produced may carry an absolute local path** —
  `run-script-tests.py` greps the skill directory; run metadata records the
  repo name from the git remote, never the checkout path.
- **Execution boundary (RFP §3):** sub-agents read and return JSON. The
  parent alone runs the target's existing tests via `run.py exec`, from an
  empty environment plus allowlisted variables, with a time limit, and only
  for commands `commands.json` allows. `run.py exec` cannot block the
  network; commands that reach it are forbidden in the ledger instead.
- **Evidence kinds:** `source` (decidable from source alone) or
  `existing_test` (a run under `checks/`). A source-only `confirmed` is shown
  with its kind in the report and gets a capped confidence — this is a user
  decision recorded in the RFP; do not re-open it.
- **Default output is `~/code-audit-runs/<repo>/run-<N>`**; a directory inside
  the target is refused by realpath comparison, never by name.
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
