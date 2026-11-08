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

**Status: Phase 1 complete (cuts 1–5), not released.** The five bookkeeping
scripts, the data contracts, the four hunting-class files (52 classes, 123
citations verified against the knowledge, ADR and origin checkouts on
2026-11-08) and the six-phase SKILL.md for both profiles exist and are
tested over the fixture repository. Two pre-release independent
verification rounds ran on 2026-11-08 and their adopted findings are applied
(cuts 4 and 5; triage in `docs/{ja,en}/reviews/`); the rounds stop here, the
second having found no high defect in the scripts. Phase 3: three of the
four E2E runs are done with cost recorded (`docs/{ja,en}/reviews/`) and cut 8
applied their lessons; left are the `web-fetch` standard run and the v0.1.0
release.

## Key commands

| Command | Purpose |
|---------|---------|
| `make check` (= `make test`) | Structural validation + script behaviour tests (89 tests) |
| `make install` | Build the zip and unpack it into `~/.claude/skills/code-audit` |
| `make install DEST=<path>` | Unpack into a custom skills directory |
| `make uninstall` | Remove the installed copy |
| `make package` | Build `dist/code-audit-vX.Y.Z.zip` (zip root = skill folder) |
| `make clean` | Remove `dist/` |

Bundled scripts (stdlib-only Python 3.9+; `--help` on each):

| Script | Subcommands | Owns |
|--------|-------------|------|
| `run.py` | `init`, `approve [--budget N]`, `nonce`, `set-budget`, `count [--agent [--rerun]]`, `set-status`, `validate`, `exec` | `run-metadata.json`, `checks/<id>.log`, `cache/` (toolchain caches `exec` redirects) |
| `ledger.py` | `seed [--prior]`, `architecture`, `assign`, `record`, `merge-critic`, `merge-candidates`, `brief hunter|critic|verifier|reverifier`, `decide`, `defer`, `abandon`, `estimate`, `validate`, `status` | `coverage-ledger.json`, `candidates.json`, `architecture.md` (and appends hunter notes to `notes.json`) |
| `findings.py` | `validate`, `add [--replace --by <agent> [--confirmed-by <agent>]]`, `digest`, `note` | `findings.json`, `replacements.json`, `notes.json` (`digest` writes back the record file it is given) |
| `compile.py` | (run dir) | `REPORT.ja.md`, `REPORT.md`, `NEEDS-VALIDATION.ja.md`, `NEEDS-VALIDATION.md` |
| `classes.py` | `list`, `size`, `check-knowledge [--adr] [--origin]` | nothing; checks `classes/*.md` |

## Directory structure

```
code-audit/
├── code-audit/              The skill — the only thing that ships
│   ├── SKILL.md             Security preamble, two modes, the six phases, the three sub-agent contracts
│   ├── classes/             Hunting classes: generic.md + mcp-server.md, cli.md, agent-runtime.md
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
| `checks/<id>.log` | `run.py exec` | command, allowed variable names, the cache variables set, exit code, duration, stdout/stderr |
| `cache/` | `run.py exec` | `GOCACHE`, `XDG_CACHE_HOME`, `PYTHONPYCACHEPREFIX` of the commands it runs (`GOPROXY=off`, `GOFLAGS=-mod=readonly`, `GOTOOLCHAIN=local`: no downloads) |
| `coverage-ledger.json` | `ledger.py` | units: canonical refs → `coverage_id`, starting paths + `source_digests`, prior_status, state, owner, checks, fingerprints, decisions, archived `attempts` |
| `candidates.json` | `ledger.py` | `candidates` (hunter-proposed, pending), `carried` (from prior runs), `decided`, `suppressed` (prior rejected, same source), `uncovered`, `resolved_prior_leads`, `merged` (duplicates folded into a kept fingerprint), `prior_leads` (`lead` notes of prior runs, for the critic) |
| `findings.json` | `findings.py` | decided records, sorted by fingerprint |
| `replacements.json` | `findings.py add --replace` | every re-verification replacement: previous and new verdict, the strengthened fields, who wrote it, who confirmed it |
| `notes.json` | `ledger.py record` / `findings.py note` | hardening, out-of-scope and lead notes with the author's agent id |
| `architecture.md`, `proposals.json`, `agents/<id>.json` | the parent | reconnaissance summary, the unit proposals given to `seed`, the raw return of every sub-agent |
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
  record that passes the findings bar, and unit `reviewed_paths` include
  every path a check names (extra paths are dropped; the union is stored).
- **E2E-derived controls (cut 6)**: `run.py count --agent` refuses an id it
  already holds unless `--rerun` says this is the same agent asked again;
  `ledger.py merge-candidates --keep --duplicate... --reason` folds
  duplicate claims before verification (the kept candidate takes the union
  of coverage ids, duplicates go to `merged` and never get a record);
  `ledger.py brief hunter|critic|verifier|reverifier` prints the sub-agent's input from the
  books; `estimate_numbers` groups `UNITS_PER_HUNTER` units per hunter,
  expects `CANDIDATES_PER_UNIT` and budgets `RERUN_RATE` re-asks (measured
  on the first E2E); `run.py exec` redirects toolchain caches under
  `RUN/cache/` and forbids downloads; fingerprints may lead with a dot.
- **Cut 7 (second E2E)**: `seed --prior` matches a prior unit by
  surface × boundary × class when its coverage id does not match (a quick
  prior under standard, or the reverse) and rewrites a carried record's
  `coverage_ids` to this run's (`remapped_prior`); a unit `merge-critic`
  adds to a run with priors is `new`; `brief hunter --agent` and
  `brief reverifier --fingerprint` complete the roles; the estimate's
  constants are 0.35 candidates per unit and 10% re-asks; the report's
  replacement line varies with the strengthened count.
- **Cut 8 (third E2E)**: `ledger.py architecture RUN` composes
  `architecture.md` from `agents/recon-*.json` (refusing an absolute local
  path) and every `brief` refuses until it exists; the candidate queue keeps
  the hunter's proposal under `verdict`, which the briefs present as
  `proposed_verdict` with the root cause; `brief verifier` prints
  `required_fields` per verdict from the schema and the `file_rule`;
  `_contract.read_json` quotes the position and context of invalid JSON;
  the estimate subtracts launched critics, uses the pending count once
  hunting is over, and its constants are per profile (quick 0.45 /
  standard 0.30 candidates per unit, 15% re-asks).
- **`decide` requires the record first** (`findings.py add`), then links the
  fingerprint to units; a carried record on a still-planned unit needs
  `--agent` (the verifier becomes the owner).
- **The cost gate is a fact of the books.** `run.py approve` records the
  approval and the budget (the estimate's total when none was given);
  `ledger.py assign` refuses every hunter before it, and one that would
  spend what `estimate_numbers` reserves for critics and verifiers. Agent
  ids are used once per run (`used_agent_ids`); `assign` and `decide
  --agent` refuse a used one.
- **findings ⇄ ledger coherence.** `findings.py add` takes a record only for
  a pending candidate (or, with `--replace`, a decided one) whose coverage
  ids exist, and keeps coverage ids unchanged on replacement; `ledger.py
  validate` and `findings.py validate <run-dir>` run `cross_check` (every
  record decided with the ledger's verdict, every decision with its record);
  `compile.py` reports only decided records and lists the rest without a
  verdict. Carried prior records with no current unit go to
  `candidates.unlinked_prior`, never to the queue.
- **Places are compared by identity.** `_contract.is_inside` / `same_place`
  walk from the nearest existing ancestor and compare device and inode, so
  another case or Unicode spelling of the target cannot put the output
  inside it (reproduced before the fix). `digests_for` follows no link in
  any path component (`lstat_no_links`), refuses non-relative keys, skips
  caches and `.git`, and stops at `DIGEST_LIMITS`. A `.git` link or a gitdir
  outside the target that does not point back at it makes the target
  `unversioned`. Prior-run units and records are validated and dropped with
  a warning when they fail.
- **Everything printed is inert.** `compile.plain` strips Unicode category C
  and `code()` keeps backticks out of code spans; `forbidden_char_errors`
  refuses control characters in records, sub-agent returns, proposals and
  notes on entry; anchored schema patterns and the id rules match whole
  strings (`re.fullmatch`), so a trailing newline is not a second
  identifier; the repo name is taken from the remote URL only by shape.
- **Evidence logs are read, not just found.** `check_log_problem` reads the
  header of a `checks/` log: `timed_out: True` or `exit_code: None` means the
  command never ran, and the log is refused as `existing_test` evidence.
- **Class references are closed.** `build_unit` refuses an attack class or
  excluded block that names no shipped class (`known_class_refs`). A
  `Source:` may also be `origin:<file>#<block>` (cloudflare/security-audit-
  skill at c1c8a8c, bold class names count as headings; user decision
  2026-11-08); `check-knowledge --origin <clone>` verifies them. Files may
  be up to 16 KB; only the selected classes are pasted into a prompt.
- **A discarded hunter result has one exit: `ledger.py abandon`.** It
  archives the attempt (status `in_progress`, the reason) and returns the
  agent's units to `planned`; `assign` then refuses that agent, so the unit
  gets a fresh owner or a `defer`. `defer` takes planned and blocked units
  (a blocked unit's evidence is archived with the reason). A critic cannot
  reassign a unit whose candidates are still pending; an archived attempt
  keeps its `decisions`. `record` does not queue a claim a prior run
  rejected with unchanged sources (`suppressed_candidates`), refuses a
  candidate that carries `verdict` beside `proposed_verdict`, and requires
  its `coverage_ids` to include every unit that lists the fingerprint.
  `status` returns the `uncovered` entries and the `blocked` units' facts.
- **The replacement rule is enforced, not described.** `findings.py add
  --replace` needs `--by <agent>`; it ranks the old and new record on verdict
  (rejected < needs_validation < confirmed), `severity.overall`, `impact`,
  `likelihood`, `confidence` and `evidence_kind`, and refuses a replacement
  that strengthens any of them unless `--confirmed-by` names a different
  agent. Prose fields cannot be ranked; SKILL.md tells the parent to treat a
  widened root cause as strengthening. A verdict-changing replacement is
  followed by `ledger.py decide` again — `decide` takes a re-decision for a
  fingerprint already in `decided` and updates the units' `decisions`.
- **Candidates nobody decided stay in the queue** and `compile.py` lists
  them under "Candidates not verified" with no verdict and no severity; the
  parent sets the run `incomplete` when that happens.
- **Class files**: `## Heading`, a `Source:` line, an optional `Refines:`
  line (`classes/generic.md#Heading`; `classes.py list` prints it and refuses
  a target that is not a class) — all before any body text,
  citing `doc.md#Heading` (knowledge `docs/en/`), `ADR-NNN` or `origin:FILE.md#Block`, several
  separated by commas — the split happens only before the next reference, so
  headings may contain commas. Class references elsewhere are
  `classes/<file>.md#<Heading>` verbatim; a test checks that the fixtures'
  references resolve to shipped classes and that SKILL.md names every class
  file. Keep each file under 16 KB (`classes.py size`); the hunter prompt
  pastes the selected classes verbatim.
- **SKILL.md's vocabulary is closed**: a test parses every `<script>.py
  <subcommand>` mention and checks it against the script's `--help`, and
  another checks that the first paragraph after the title is the security
  preamble. Rename a subcommand and the test names the stale mention.
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
- **git never sees the target's config.** The target's `.git/config` may
  name commands, and `-c` overrides cannot undefine a clean filter the
  repository defines (`git status` runs it when a tracked file's stat
  changed but its size did not). `run.py init` therefore builds a scratch
  git-dir — HEAD, index, refs, packed-refs, shallow, info/exclude copied,
  objects linked, a config of its own with only data keys copied (filemode,
  ignorecase, autocrlf, objectformat, refstorage) — and runs
  `git --git-dir <scratch> --work-tree <target>` with the `-c` overrides and
  a minimal environment. The remote URL is parsed from the config as text.
  Two tests plant a `core.fsmonitor` script and a `filter.*.clean` script and
  assert neither runs; the clean-filter vector was confirmed live before the
  fix. The copy itself follows no link (`O_NOFOLLOW`, `scandir` without
  following), takes regular files only, charges every entry including
  directories, and stops at `COPY_LIMITS` (bytes, files, per-file bytes,
  nesting depth); a target past the budget is recorded as `unversioned`,
  never crashed on.
- **`run.py exec` kills the whole process group** on timeout
  (`start_new_session=True` + `os.killpg`); killing only the child would
  leave a grandchild holding the pipes and the parent waiting. A test spawns
  a 30-second grandchild under a 1-second limit.
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
