# RFP: code-audit

> Generated: 2026-11-08
> Status: Draft

## 1. Problem Statement

A Claude Code Skill that audits one organization repository for
**vulnerabilities that actually cross a trust boundary**, reporting each with
its source evidence, reproduction conditions, priority and smallest fix, and
**showing what was covered in a ledger**. The user is the nlink-jp operator.

Three facts motivate it. CONVENTIONS §Verify with an independent pass requires
an independent implementation check, but no means exists for a repository-wide
vulnerability audit. The built-in `/security-review` is limited to a diff. The
knowledge base's security document records several defects that an external
review found after four internal review rounds had passed, so the demand for a
systematic audit is demonstrated.

The reference is cloudflare/security-audit-skill (MIT, version as of
2026-09-14). We keep its three-way verdict, adversarial validation, coverage
ledger, prior-run carry-over, budget gate and record-derived reports; we replace
its prose procedures with scripts, and we derive the hunting classes from the
defects actually recorded in the organization's knowledge base. No code is
reused; the design is re-implemented (ADR-024: code written outside the
organization is not shipped). The design's origin is credited in the README
and in the LICENSE third-party notice.

Setup burden check (can the intended user complete it alone): Claude Code,
`python3` (standard library only) and registering the skill zip in the app.
No cloud credentials, no external service registration.

## 2. Functional Specification

### Commands / API Surface

One SKILL.md serves two modes.

- **Guidance mode** (default): security questions, focused reviews,
  investigation of a specific suspicion. No output directory, no six-phase run.
- **Full audit mode**: only when the user explicitly asks to audit a repository.
  When a request could mean either, ask one question before creating files.

```
/code-audit <target-dir> [--output <dir>] [--profile quick|standard]
            [--budget <N>] [--prior <run-dir>]... [--knowledge <dir>]
```

| Argument | Meaning |
|----------|---------|
| `<target-dir>` | Local checkout under audit (required) |
| `--output <dir>` | Where artifacts go. Default `~/code-audit-runs/<repo>/run-<N>`. A directory inside the target (compared by realpath identity) is refused by `run.py init` |
| `--profile` | `quick` (one hunter wave, one critic, one verification stage; the subsystem dimension is collapsed to one so units are coarser) / `standard` (waves until the critic reports no remaining work; two verification stages). Default `standard` |
| `--budget <N>` | Cap on agent invocations. When omitted, the post-reconnaissance estimate becomes the cap |
| `--prior <run-dir>` | Earlier artifacts for the same repository; repeatable. Carried by fingerprint and source digest |
| `--knowledge <dir>` | Optional. Only when given, check that each hunting class's source heading exists in the knowledge base |

Bundled scripts (standard library only; called by the workflow, usable alone):

| Script | Subcommands | Role |
|--------|-------------|------|
| `scripts/run.py` | `init` / `set-budget` / `count` / `set-status` / `validate` / `exec` | Create `run-metadata.json`, record the approved budget and actual invocation counts, move the status (`in_progress` → `complete` / `incomplete` with reason). `exec` runs only commands the command ledger allows, with an empty environment plus the entry's allowlisted variables, the target as working directory and a time limit, writing output to `checks/<id>.log` |
| `scripts/ledger.py` | `seed [--prior]` / `assign` / `record` / `merge-critic` / `decide` / `defer` / `estimate` / `validate` / `status` | Build the coverage ledger (carry-over from `--prior`: `prior_status`, same-source confirmed / needs_validation records into the candidate queue, same-source rejected ones into the suppression list), assign, record hunter results, merge critic output, record verifier decisions, mark budget-starved units `deferred`, estimate, validate. Only this script knows how `coverage_id` is derived and what the state machine allows |
| `scripts/findings.py` | `validate` / `add` / `note` | Structural and semantic validation of `findings.json` (mutually exclusive verdict branches, severity ≤ impact, a confidence cap for source-only evidence, trace ordering, unique sorted fingerprints, one or more blockers). `add` appends one record at a time so the parent never rewrites the whole JSON; with `--target` it checks the cited digests against the current files and refuses a stale record. `note` files an out-of-scope observation into `notes.json` |
| `scripts/compile.py` | (run dir only) | Derive `REPORT.ja.md` / `REPORT.md` / `NEEDS-VALIDATION.ja.md` / `NEEDS-VALIDATION.md` from `findings.json`, the ledger, `candidates.json` and `notes.json` |
| `scripts/classes.py` | `list` / `size` / `check-knowledge --knowledge <dir> [--adr <dir>]` | Parse the class files, check their size, and check that each class's source (knowledge document + heading, or organization ADR number) exists |

(Adjustment made while implementing on 2026-11-08: carry-over lives in
`ledger.py seed --prior` rather than `findings.py carry`. Carry-over sets the
ledger's `prior_status` and the candidate queue at once, so one script
writing both keeps the ownership boundary simple.)

### Input / Output

Input is the target's local checkout and, optionally, earlier artifacts.

Contents of the output directory:

| File | Writer | Content |
|------|--------|---------|
| `run-metadata.json` | `run.py` only | run_id, repo name (from the git remote; no absolute paths), source ref and dirty flag, profile, budget, actual invocation count, run_status with reason |
| `architecture.md` | parent | reconnaissance summary (about 1,000 words max) |
| `commands.json` | parent (a reconnaissance artifact) | ledger of the target's test and check commands. Each row: allowed or forbidden, the reason when forbidden (reaches the network, reads credentials, writes outside the target, fetches dependencies), write locations, time limit |
| `coverage-ledger.json` | `ledger.py` only | coverage ledger: units of surface × boundary × subsystem × attack class with state, and the source digest of each path a unit cites |
| `candidates.json` | `ledger.py` only | candidates awaiting validation (hunter proposals), carried records, decided ones, claims suppressed as rejected in a prior run, unassigned surfaces, resolved prior leads |
| `findings.json` | `findings.py` only | `confirmed` / `needs_validation` / `rejected` records sorted by fingerprint; each record carries the source digest of the paths it cites |
| `notes.json` | `ledger.py record` and `findings.py note` | out-of-scope observations and hardening notes returned by hunters and verifiers |
| `checks/<id>.log` | `run.py exec` only | record of each existing-test run (command, allowlisted variable names, exit code, output) |
| `REPORT.ja.md`, `REPORT.md` | `compile.py` | human-facing report; verdicts, severity, evidence kind and coverage summary derived from records |
| `NEEDS-VALIDATION.ja.md`, `NEEDS-VALIDATION.md` | `compile.py` | unresolved leads, no severity |

The data contract is `schema.json` (three findings branches, ledger unit,
metadata, commands). Severity calibration (the five anchors and the
high/medium discriminator) lives in `references/severity.md`, and
`findings.py validate` fixes its vocabulary and arithmetic.

Hunters, critics and verifiers start **read-only**: they write no files, run
no commands and return one JSON object. The parent passes it through
`ledger.py record` / `decide` and `findings.py add` before anything is merged.
Should a sub-agent write something anyway, it is not evidence. The reference's
scratch/artifacts split and eleven-step promotion procedure are unnecessary in
this arrangement.

### Configuration

No configuration file, no environment variables. Flags only.

### External Dependencies

- Claude Code (an environment with the Agent tool; full audit mode runs only here)
- `python3` 3.9 or later, standard library only
- the target repository's own toolchain (`go`, `uv`, …) to run its tests;
  when absent, the affected check falls to `needs_validation`
- no credentials handled

Where data goes, listed. The skill itself connects nowhere. The target's code
and the artifacts reach this session's model backend like any other session
content. The target's test commands may reach wherever its `Makefile` sends
them, so commands that reach the network, fetch dependencies or read
credentials are recorded as forbidden in `commands.json` during reconnaissance
and the parent never runs them.

## 3. Design Decisions

### Kept from the reference

- **Three-way verdict.** `confirmed` has a complete trace and evidence;
  `needs_validation` has one or more decisive unresolved facts and no severity;
  `rejected` records a refuted candidate so the next run does not repeat it.
- **The finder never verifies.** Each candidate goes to a different, fresh
  sub-agent whose role is to refute it. Same principle as the knowledge base's
  "self-approval is not a defence".
- **The ledger is the only coverage claim.** Agent counts and sentences such as
  "auth was reviewed" are not coverage evidence. `ledger.py validate` enforces
  the unit state machine.
- **Carry-over by fingerprint.** The same root cause keeps the same fingerprint
  across verdict states. Change is judged by the source digests that records
  and ledger units carry for the paths they cite (a prior source ref alone is
  no evidence that nothing changed). A prior `confirmed` goes back through
  verification; a prior `rejected` suppresses only the same claim, never
  re-inspection of its unit.
- **Budget reserves critics and verifiers first**; hunters run on the rest.
  Exhaustion records `run_status: incomplete` with its reason, stated at the
  top of the report.
- **Two verification stages (standard).** Candidate validation (the refuter)
  and independent re-verification of the final record (a different fresh
  reader) are separate. When the re-verifier returns a replacement that
  strengthens the verdict, root cause, impact or severity, yet another fresh
  verifier confirms it before it is applied. Wording and line-number
  corrections are applied directly. `quick` uses one stage (the candidate
  verifier also performs the record check).
- **Reports are derived from records**; prose never changes a verdict,
  severity or impact.

### Changed from the reference

- **Scripts keep the books; the model decides.** The reference spells out the
  percent-encoding rules for `coverage_id` and an eleven-step fd-based file
  promotion procedure in prose and has the model execute them by hand.
  Following the knowledge base ("don't write prose don't-lists; put controls out
  of band") and the workspace lesson that prose procedures get skipped, ledger
  seeding, assignment, updates, estimation and validation, record insertion and
  report derivation all live in stdlib Python. The parent edits neither the
  ledger JSON nor `findings.json` by hand; it hands each item to a script. Same
  pattern as compliance-review's `coverage.py` and weather-forecast's "the
  model only words the answer".
- **Validators in Python.** The reference ships Node.js `.cjs` validators. The
  organization's skills are uniformly stdlib-only Python, and ADR-024 bars
  shipping outside code, so the design is referenced and re-implemented.
- **The target is adversarial input.** The reference does not address prompt
  injection from the audited code. The top of SKILL.md states that comments,
  strings, documents and test names are data, never instructions. Hunter and
  verifier output is one strict JSON object; anything that fails script
  validation is discarded, not repaired. Out-of-scope observations get a
  destination (`findings.py note`) so they are not folded into findings (the
  negative space of the output contract). Quoted code appears in reports only
  inside fenced blocks.
- **Hunting classes come from the organization's defect history.** Beside the
  generic classes (injection, access control, resource/file handling, crypto,
  business logic, feature abuse, chained, wildcard, obvious things), v1 ships
  dedicated classes for three organization product types. Each class carries a
  source: either a knowledge document name plus heading, or an organization
  ADR number, with the kind recorded in the class.

  | File | Product type | Example source lessons |
  |------|-------------|------------------------|
  | `classes/mcp-server.md` | MCP server | TOCTOU where a resolved path is checked and the original opened (security.md); probing writability by writing (security.md); server-authored metadata treated as fact (security.md); writes outside the work_dir contract (ADR-021 / mcp-server-design.md) |
  | `classes/cli.md` | Go / Python CLI | environment leaking to child processes (security.md); credentials quoted in URL or config syntax errors (security.md); silent fallback to defaults (ADR-026 / config-and-io.md); cleaning up from what was planned instead of what was created (security.md) |
  | `classes/agent-runtime.md` | LLM agent runtime | self-approval; guards keyed on a refusal flag; agent-writable persistent memory; permissions premised on "only a human writes this"; a constraint that can loosen is a permission (all security.md) |

  The knowledge base is the origin; the skill carries a copy. The check is
  written the day the copy is: `classes.py check-knowledge` runs only when
  `--knowledge <dir>` is given and is skipped otherwise (a standalone clone's
  `make check` does not depend on the knowledge base, the reason behind
  ADR-006). New lessons are followed at release time.
- **Execution boundary: reading plus existing tests only** (user decision,
  2026-11-08). The only code run is the target repository's own tests and
  checks, which reconnaissance identifies from its `Makefile` or CI definitions
  and writes to `commands.json` as allowed or forbidden with reasons. A command
  not in the ledger is never run. **Only the parent runs them**, through
  `run.py exec`, which starts from an empty environment with allowlisted
  variables only, applies a time limit and keeps the output under `checks/`.
  Hunters and verifiers run nothing (this avoids the flakes and cost of N
  agents running `make test` concurrently in one checkout). Hunters may not
  write new fixtures or harnesses that execute target code in v1.
  A `confirmed` record's `evidence.kind` is either `source` (decidable from
  source alone: a control is absent, or a sibling path bypasses it) or
  `existing_test` (a run recorded under `checks/` shows the result).
  **A source-only record is always shown with an evidence-kind column in the
  report's confirmed table, and `findings.py validate` caps its confidence.**
  The verifier must reconstruct the "preventing layers" (handler registration,
  upstream middleware, configuration defaults) before deciding (user decision,
  2026-11-08; the tension with ADR-023 "reading yields a hypothesis" is
  resolved by showing the evidence kind mechanically).
  **Residual risk**: a `confirmed` may be issued without observing runtime
  reachability. Because an existing test rarely demonstrates a vulnerability,
  most `confirmed` records are expected to be `source`. The refuting verifier,
  the visible evidence kind, the confidence cap and the rule that a decisive
  runtime fact drops the record to `needs_validation` absorb it. `run.py exec`
  does not block the network; network-reaching commands are only forbidden by
  the ledger, which is recorded as a residual risk too. The OS sandbox the
  reference demands does not exist in the organization, and demanding it in
  prose would not make it so. Execution inside a container (data-toolbox's
  Podman pattern) is a Phase 2 candidate decided by its own ADR.
- **Sub-agents are read-only.** Hunters, critics and verifiers return JSON,
  write no files and run no commands. This removes the reference's
  scratch/artifacts separation and promotion procedure entirely; the ledger's
  `local_checks.artifact` becomes a reference to `checks/<id>.log`.
- **Reconnaissance is four fixed roles** (product, stack and runnable commands;
  principals, authority and controls; entry surfaces, copies and sinks;
  existing tests and deployment visibility), run as parallel sub-agents. They
  run before the cost gate, so their count is announced before the run starts.
- **The cost gate is human-in-the-loop.** After reconnaissance,
  `ledger.py estimate` derives the invocation cap (expected hunters + critics +
  verifiers) from the unit count and adds an expected token volume from the
  input size measured during reconnaissance; the user approves or lowers
  `--budget` before hunting starts. The actual count and the termination reason
  go into `run-metadata.json`. Workspace lesson: estimate and state the cost
  before running anything that calls a paid model repeatedly, and count it
  afterwards.
- **Two profiles, quick / standard.** The reference's `deep` (per-lifecycle
  unit split, re-inspection of prior covered units) is dropped.
- **Reports in Japanese and English**, both compiled from the same records by
  `compile.py`.
- **The name is code-audit.** It audits our own code. It sits beside the
  existing `*-review` (reads our own material) and `*-research` (reads the web)
  naming lines and does not collide with the built-in `/security-review`.

### Complements

- built-in `/security-review`: diff review. code-audit covers the whole repository.
- compliance-review: regulation × application. code-audit: code × trust boundary.
- cve-lookup / govulncheck: known-vulnerability matching. code-audit hunts unknown defects.
- security-reviews (private records repository, ADR-020): the natural home for
  artifacts, chosen by the user through `--output`. The skill does not know it.
  Artifacts carry no absolute paths so that they can be placed there.

### ADR-023 / ADR-027 check

It takes on no OS-managed role. It is a cross-cutting procedure, not one tool's
craft, so a standalone skills-series skill is correct rather than a skill
bundled with a tool.

### Explicitly out of scope

- Diff review (left to the built-in)
- Any contact with deployed environments, external services or shared infrastructure
- Known-vulnerability matching of dependencies (cve-lookup, govulncheck)
- Modifying the target. Fixes are described, never applied
- Auditing several repositories in one run
- Full audit outside Claude Code (the claude.ai chat surface has no Agent tool,
  so guidance mode only there; Claude Code inside the desktop app is supported)
- Running new fixtures, sandboxes, the `deep` profile (Phase 2 or later, separately)
- Runs scoped to paths or to the span between two commits (Phase 2)

## 4. Development Plan

### Phase 1: Core

Everything here completes inside this repository. By user decision
(2026-11-08) quick / standard and carry-over stay in Phase 1, split into three
review cuts.

1. **Scripts and contracts**: fix `schema.json`, `references/severity.md` and
   the five scripts (`run.py`, `ledger.py`, `findings.py`, `compile.py`,
   `classes.py`) with unittest first, driven by `tests/run-script-tests.py`.
   Test material: a small sample repository with deliberate defects
   (`tests/fixtures/`) plus hand-written valid and invalid ledgers, findings
   and command ledgers. Include tests that pin the "always X" claims: SKILL.md
   contains no instruction to write the ledger or findings directly,
   `compile.py` output never places code outside a fence, `coverage_id`
   derivation exists only in `ledger.py`, and `run.py exec` refuses commands
   absent from or forbidden by the ledger.
2. **The quick flow**: the hunting classes (one generic file and three
   organization files, each class with source and kind; `classes.py size`
   keeps each file around 8 KB) and SKILL.md: adversarial-input discipline at
   the top, guidance vs full audit with the one question for ambiguous
   requests, the six phases (reconnaissance → hunting waves → candidate
   validation → structured output → independent re-verification → report), the
   cost gate, the output contracts for hunters, critics and verifiers
   (including their negative space), and the verifier's reconstruction of
   preventing layers.
3. **Standard waves and carry-over**: critic waves (`merge-critic`), the two
   verification stages with the replacement rule, `--prior` carry-over
   (`carry`, source digests).
4. `make check` (structural validation + script tests; `--knowledge` optional).

Independently reviewable cuts: (1) is deterministic and judged by tests alone.
(2) is the SKILL.md flow and class content, judged by reading. (3) builds on (2).

### Phase 2: Features

- Scoped runs: `--paths` and `--since <ref>` (the span between two commits as units)
- More product types: macOS GUI (XPC, Seatbelt), Skill (SKILL.md's own injection surface)
- Minimal reproduction inside a container (separate ADR; Podman becomes a
  precondition, so adoption is decided separately. It would add `local` to
  `evidence.kind` and reduce `confirmed(source)`)
- PDF output through report-studio (optional)

### Phase 3: Release

- README.md / README.ja.md, CHANGELOG.md, AGENTS.md. Credit
  cloudflare/security-audit-skill (MIT) as the design's origin in the README
  and the LICENSE third-party notice
- E2E: two real organization repositories (one MCP server, one CLI), `quick`
  and `standard` once each. Record invocations, tokens and cost; compare with
  the estimate
- Independent verification passes: at design freeze (against this RFP; the
  first was run on 2026-11-08) and before release (against the implementation)
- Release v0.1.0 per the CONVENTIONS release checklist (umbrella submodule
  pointer, org profile, site catalog and knowledge feedback are checklist items)

### Dependencies (not plan steps; left to their owners)

- Where the knowledge base's wording turns out insufficient as a hunting
  instruction while writing the classes, open an issue in nlink-jp/knowledge.
  Not a step of this plan.

## 5. Required API Scopes / Permissions

None. No external services and no credentials.

## 6. Series Placement

Series: skills-series
Reason: it is a Claude Code Skill and follows one-repository-per-skill
(ADR-004). As a skill that automates part of the development process (the
independent pass), it sits beside compliance-review and incident-review.

## 7. External Platform Constraints

- **Claude Code's Agent tool**: sub-agents cannot nest; the parent does all
  assignment and merging. A sub-agent returns text, so a step that extracts the
  JSON and validates it by script is always required. One invocation is the
  unit of cost. Whether sub-agent cost can be read in tokens is unverified; if
  not, it is estimated from reconnaissance measurements.
- **Hunter prompt size**: the reference pastes class bodies verbatim. Keep each
  class file around 8 KB and paste only the selected classes.
- **claude.ai chat surface**: no Agent tool, so guidance mode only. The
  SKILL.md `description` must be at most 1,024 characters (registration refuses
  longer; `make check` stops it). gem-agent reads the same limit.
- **Script runtime**: `python3` standard library only. `run.py exec` can empty
  the environment and apply a time limit but cannot block the network.
- **Running the target's tests**: without the target's toolchain on the host,
  `existing_test` evidence cannot be obtained and the record falls to
  `needs_validation`. The report states this.

---

## Discussion Log

- **2026-11-07 evaluation**: read cloudflare/security-audit-skill (commit
  c1c8a8c) in full. Six designs to keep (three-way verdict, adversarial
  validation, coverage ledger, fingerprint carry-over, budget gate,
  record-derived reports) and five to change (script the prose procedures,
  Python stdlib, treat the target as adversarial input, classes from the
  organization's defect history, execution boundary). No existing skill of the
  same kind. The user chose to draft an RFP.
- **2026-11-08 name and scope**: name `code-audit` (alternatives: vuln-hunt,
  security-audit). v1 targets one whole repository (path scoping and
  series-wide runs deferred). Execution boundary is reading plus existing tests
  (container execution and reading-only rejected).
- **2026-11-08 artifacts and classes**: artifacts go to a user-chosen
  directory, default outside the target (a gitignored directory inside the
  target was rejected: risk of accidental commit in public repositories).
  Hunting classes are bundled with the knowledge base as their source (reading
  the knowledge repository at run time was rejected: it needs a configured
  location and the lessons are not written as hunting instructions; generic
  classes only was rejected: it discards the differentiation). Reports in
  Japanese and English. Cost: show the estimate after reconnaissance and wait
  for approval.
- **2026-11-08 platform and plan**: full audit on Claude Code only
  (agent-neutral wording grows long through abstraction and only one platform
  can be measured). Two profiles, quick / standard (deep dropped). Prior-run
  carry-over from Phase 1 (user decision: re-runs will be the normal usage).
  v1 organization classes: MCP server, Go/Python CLI, LLM agent runtime
  (macOS GUI / Skill in Phase 2).
- **2026-11-08 independent verification pass (design freeze)**: a verifier in
  a separate context checked the first draft against CONVENTIONS, organization
  ADRs, the knowledge base, workspace memory and the reference projects. Main
  findings adopted: letting hunters run existing tests leaves "writes nothing,
  reaches no network, touches no credentials" as prose only → centralize test
  execution in the parent's `run.py exec` and make `commands.json` (allowed /
  forbidden with reasons) a reconnaissance artifact. The parent rewriting
  `findings.json` whole → `findings.py add`, one record at a time. A
  cwd-relative default output can land inside the target → `~/`-based default
  plus realpath comparison. Sources exist beyond security.md → widen to
  document name + heading or ADR number. The copy's check is written the day
  the copy is → optional `--knowledge`, moved to Phase 1. No basis for judging
  change on carry-over → source digests on records and units. Inconsistent
  verification-stage wording → standard two stages, quick one, plus the
  replacement rule. No absolute paths in artifacts. Cost in expected tokens,
  not only counts. A home for the severity calibration rules. Coarser quick
  units. Inspired-by attribution. Two ja/en mismatches corrected.
  Two points put to the user: treat source-only evidence as `confirmed`? →
  **yes, with the evidence kind always shown in the report and a confidence
  cap** (the alternative "reading-only is needs_validation" was rejected
  because v1 reports would consist mostly of leads). Phase 1 weight → **keep
  everything in Phase 1**, split into three review cuts (the alternative
  "v0.1.0 is quick only" was rejected).
- **Design simplification**: because sub-agents are read-only, the reference's
  scratch/artifacts separation and eleven-step promotion procedure became
  unnecessary, and `local_checks.artifact` became a reference to the
  parent-written `checks/<id>.log`.
