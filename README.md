# code-audit

A Claude Code Skill that audits one repository of your own code for
vulnerabilities that actually cross a trust boundary, and shows what was
covered in a ledger. Design: the [RFP](docs/en/code-audit-rfp.md)
(Japanese primary: [RFP (ja)](docs/ja/code-audit-rfp.ja.md)).

> **Status: v0.1.0.** The bookkeeping scripts, the data contracts, the
> hunting classes and the six-phase SKILL.md exist for both profiles, with
> tests over a fixture repository. Before the release: four end-to-end runs
> on two real repositories with the cost recorded (`docs/{ja,en}/reviews/`)
> and two independent verification rounds over the implementation.

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
[Releases](https://github.com/nlink-jp/code-audit/releases), then
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
judging; independent re-verification (`standard`) under a replacement rule
— a re-verifier's replacement that keeps or weakens a record is applied, one
that strengthens the verdict, severity, confidence or evidence kind is
refused by `findings.py add` until a second fresh verifier confirms it; and
the compiled reports. With `--prior <run-dir>`, prior `confirmed` and
`needs_validation` records whose cited sources are unchanged are re-verified
first, prior `rejected` claims are suppressed (the unit is still hunted), and
every unit carries what the last run concluded for it.

Hunting classes (`code-audit/classes/`): `generic.md` for every repository
and one file per product type — `mcp-server.md`, `cli.md`,
`agent-runtime.md`. Each class cites where its lesson is recorded: a heading
of the organization's knowledge base, an organization ADR, or — for the
general know-how the organization has not had to learn the hard way — a
block of the origin skill, restated in our words. `classes.py
check-knowledge --knowledge <dir> [--adr <dir>] [--origin <dir>]` verifies
every citation against the checkouts.

What the scripts hold, so the workflow does not have to: no hunter is
assigned before the human's approval is recorded (`run.py approve`) or past
the budget reserved for critics and verifiers; a record enters the findings
file only for a claim the ledger holds, and both validators cross-check the
two; a log of a test that never ran is not evidence; places are compared by
identity, not by name; every value the report prints is made inert first.
From the first end-to-end run (`docs/en/reviews/2026-11-08-e2e-smoke-webhook-relay.md`):
a counted launch is counted again only as a declared re-ask (`run.py count
--rerun`); duplicate claims are folded before any verifier is spent
(`ledger.py merge-candidates`); the critic's and the verifier's inputs are
printed from the books (`ledger.py brief`) so no coverage id is retyped;
toolchain caches land under the run and downloads are off (`run.py exec`);
the estimate counts hunters by grouping and budgets re-asks; `lead` notes
reach the next run's critic through `seed --prior`. From the second run
(`docs/en/reviews/2026-11-08-e2e-standard-webhook-relay.md`): every role's
input is printed from the books (`ledger.py brief hunter|critic|verifier|reverifier`),
and a prior run of the other profile still carries over, matched by
surface × boundary × class. From the third run
(`docs/en/reviews/2026-11-08-e2e-quick-web-fetch.md`): the reconnaissance
synthesis `architecture.md` is composed by a script from the saved returns
(`ledger.py architecture`) and no role's brief prints without it; the briefs
carry the candidate's proposed verdict and root cause and the required fields
of each verdict; invalid JSON is refused with its position and context; the
estimate subtracts launched critics, uses the real queue once hunting is
over, and takes a per-profile candidate rate. From the fourth run
(`docs/en/reviews/2026-11-08-e2e-standard-web-fetch.md`): the nonce sits on
both wrapper tags; a return that spells the operator's login or an absolute
local path is refused wherever it enters the books (the agent describes,
never spells); the hunter's brief lists the files under its units' starting
paths; the verifier's brief names the fields of trace and evidence entries;
the estimate counts the re-verification of decided records; the report
counts weakening replacements apart from wording fixes. From the first
production run (`docs/en/reviews/2026-11-09-standard-gem-agent.md`, an agent
runtime, standard, no prior): a confirmed record answers whose act makes the
path happen and which record decided the behaviour, and an operator-composed
path whose behaviour a record decided is not a finding (rule 3, refused by
`findings.py add`; the gap in what the operator reads is a `documentation`
note); the estimate prices a unit no prior run hunted at twice the rate of
one that follows a prior and prints the shortfall; the owner's acceptance of
a finding is logged in the run (`findings.py accept`) and the next run
neither re-verifies nor re-reports it while its sources are unchanged.
Residual risks are in the RFP: the target's own tests run unsandboxed as
your user, and whether a sub-agent really has no shell depends on the agent
type the runtime offers.

## Development

```
make check      # structural validation + script behaviour tests
make package    # dist/code-audit-vX.Y.Z.zip (zip root = skill folder)
```

Bundled scripts are stdlib-only Python 3.9+ (`--help` on each): `run.py`
(run metadata, bounded execution of the target's existing tests),
`ledger.py` (coverage ledger and candidate queue), `findings.py` (findings
records, digests, notes and the owner's dispositions), `compile.py` (reports), `classes.py`
(hunting-class checks). Rules for contributors and agents: [`CLAUDE.md`](CLAUDE.md),
[`AGENTS.md`](AGENTS.md).

## Acknowledgement

The workflow design derives from
[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill)
(MIT). No code and no verbatim text from it is included; the design was
re-implemented under the organization's conventions, and the generic hunting
classes restate its attack-class lenses in our words, each citing the block
it derives from as an `origin:` source. See the third-party notice in
[`LICENSE`](LICENSE).

## License

MIT — see [`LICENSE`](LICENSE).
