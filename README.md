# code-audit

A Claude Code Skill that audits one repository of your own code for
vulnerabilities that actually cross a trust boundary, and shows what was
covered in a ledger. Design: the [RFP](docs/en/code-audit-rfp.md)
(Japanese primary: [RFP (ja)](docs/ja/code-audit-rfp.ja.md)).

> **Status: under construction.** The bookkeeping scripts, the data
> contracts, the hunting classes and the six-phase workflow of SKILL.md exist
> and are tested for the `quick` profile. The `standard` profile's later
> hunting waves, second verification stage and `--prior` carry-over are the
> next cut; SKILL.md says so and runs `quick` until then. v0.1.0 ships both.

**What it will do.** The parent agent runs six phases over isolated
sub-agents: reconnaissance; coverage-led hunting waves; adversarial validation
of every candidate by a fresh verifier that tries to refute it;
schema-validated `findings.json` with three verdicts — `confirmed` (complete
trace and evidence, with severity), `needs_validation` (an exact unresolved
fact, no severity), `rejected` (a refuted claim, kept so the next run does not
repeat it); independent re-verification of the final records; and a
Japanese/English report derived from the records, never the other way round.

**What makes it ours.** Bookkeeping — the coverage ledger, the findings file,
run metadata, the cost estimate, the reports — is done by bundled stdlib
Python scripts, one item at a time; the model decides and the scripts record.
Hunting classes come from the defects the organization actually shipped and
recorded in its knowledge base (MCP servers, CLIs, LLM agent runtimes) beside
the generic classes. The audited repository is treated as adversarial input.
Sub-agents are read-only; only the parent runs the target's existing tests,
and only the commands a reconnaissance ledger allows. A cost gate shows the
expected number of agent invocations before hunting starts and waits for
approval.

## Install

Download `code-audit-vX.Y.Z.zip` from
[Releases](https://github.com/nlink-jp/code-audit/releases) (none yet), then
register it:

- **In the app** (Claude Desktop, claude.ai, mobile) — add the zip from the
  skill settings (Customize → Skills). Prefer this route; it survives changes
  to where skills are stored on disk.
- **Claude Code** — `unzip code-audit-vX.Y.Z.zip -d ~/.claude/skills/`, or
  into a project's `.claude/skills/` for a project-scoped install.

From a checkout:

```bash
make install
```

That builds the release zip and unpacks *that*, so what you run is what a
release ships. `make install DEST=/path/to/skills` installs elsewhere;
`make uninstall` removes it.

## Usage

```
/code-audit <target-dir> [--output <dir>] [--profile quick|standard]
            [--budget <N>] [--prior <run-dir>]... [--knowledge <dir>]
```

The full audit runs in Claude Code only (it needs the Agent tool). On the
claude.ai chat surface the skill answers in guidance mode. Artifacts go to a
directory you choose, by default `~/code-audit-runs/<repo>/run-<N>`, never
inside the target. See the RFP for the artifact layout and the execution
boundary.

The six phases: reconnaissance by four read-only roles (product and runnable
commands; principals and defences; entry points and sinks; existing tests and
what only deployment can tell), which also produces the command ledger and
runs the allowed tests once; a cost gate that shows the expected number of
agent invocations and waits for approval; hunting over ledger units, each
hunter reading only its units' classes; adversarial verification of every
candidate by a fresh agent that reconstructs the preventing layers before
judging; independent re-verification (`standard`); and the compiled reports.

Hunting classes (`code-audit/classes/`): `generic.md` for every repository
and one file per product type — `mcp-server.md`, `cli.md`,
`agent-runtime.md`. Each class cites where the organization recorded the
lesson (a heading of the knowledge base or an ADR); `classes.py
check-knowledge --knowledge <dir> [--adr <dir>]` verifies the citations
against a checkout.

## Development

```
make check      # structural validation + script behaviour tests
make package    # dist/code-audit-vX.Y.Z.zip (zip root = skill folder)
```

Bundled scripts are stdlib-only Python 3.9+ (`--help` on each): `run.py`
(run metadata, bounded execution of the target's existing tests),
`ledger.py` (coverage ledger and candidate queue), `findings.py` (findings
records and notes), `compile.py` (reports), `classes.py` (hunting-class
checks). Rules for contributors and agents: [`CLAUDE.md`](CLAUDE.md),
[`AGENTS.md`](AGENTS.md).

## Acknowledgement

The workflow design derives from
[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill)
(MIT). No code or text from it is included; the design was re-implemented
under the organization's conventions. See the third-party notice in
[`LICENSE`](LICENSE).

## License

MIT — see [`LICENSE`](LICENSE).
