# E2E run 3 (2026-11-08) — web-fetch / quick

Subject: skill at `cc04ab7` (after cut 7). `nlink-jp/web-fetch` (source ref
`bdc77d3…`, clean). One full pass of Phases 0–6 in the quick profile, no
prior. The findings live in the run directory's `REPORT.md` and
`NEEDS-VALIDATION.md`; this page keeps what the skill learned.

## Facts of the run

| Item | Value |
|---|---|
| Budget (approved) | 34 → 41 → 43 (three cost gates: 34 after reconnaissance, +7 when 16 candidates appeared, +2 when re-asks exhausted it) |
| Actual | 43 (reconnaissance 4, hunter 18 [14 + 4 re-asks], critic 1, verifier 20 [16 + 3 re-asks + 1 fresh]) |
| Coverage units | 37 → 38 (the final critic added one, deferred under quick: panic reachability from fetched content; hunter-14 had established that nothing recovers on the entry path) |
| Candidates | 16 (one duplicate: hunter-3's and hunter-12's userinfo claims were folded by `record` as one fingerprint) |
| Verdicts | confirmed 6 (medium 1, low 5), needs_validation 1, rejected 9 |
| Confirmed | rendered-size amplification by nested blockquote / list prefixes (medium); release builds without `-trimpath`; linux tar owner names; the CLI prints fetched text to the terminal with escape sequences intact; README's promise that a project's MCP configuration can never open the LAN, plus a relative XDG_CONFIG_HOME accepted (the verifier narrowed the claim before confirming); `<base href="javascript:">` slips past the scheme filter |
| needs_validation | the remote Content-Type spliced unquoted into the isError message (decided by whether the runtime's nonce wrap covers isError results) |
| Why rejected | control belongs to the runtime 3 (config link/owner checks, internal DNS disclosure, NAT64 network-specific prefix); no documented contract 3 (3x cache, title bound, x-user-defined remap); self-impact 1 (userinfo echo); false premise 1 (zoned answers: the standard library drops zones); no path to a user 1 (brew formula gate) |
| Allowed commands | `go test ./...`, `go vet ./...` (both exit 0, offline through the E6 cache redirection) |
| Notes | 112 (hardening 72, lead 28, out_of_scope 12) |
| run_status | complete |
| Absolute paths or user names in the output | none |

## Measured cost (tokens per sub-agent)

| Role | Count | Mean | Range |
|---|---|---|---|
| reconnaissance | 4 | not recorded (the notifications were lost to context compaction) | run 2's ≈ 101k assumed |
| hunter | 14 | ≈ 112k | 89k–186k (hunter-14, holding the whole-tree and secrets units: 186k, 39 tool calls) |
| hunter re-asks | 4 | ≈ 140k | 107k–193k |
| critic | 1 | ≈ 144k | brief of 152 KB (37 units, 16 candidates, 11 uncovered) |
| verifier | 17 | ≈ 99k | 69k–124k |
| verifier re-asks | 3 | ≈ 95k | 72k–110k |

About 4.24M measured (without reconnaissance) plus about 0.4M assumed for
reconnaissance ≈ 4.6M tokens over 43 launches, about 1.3× the 34-launch /
3.4M estimate. The gap: 16 candidates against 13 expected (0.43 per unit, the
constant says 0.35), and 7 re-asks plus 1 fresh verifier against 2 expected
(7 of 36 first returns = 19%, the constant says 10%).

## Deviations from the procedure (recorded)

- `architecture.md` was never written; the hunters got a reconnaissance
  summary inline in their prompts. It surfaced at the critic step and was
  composed mechanically from the four reconnaissance returns (E21).
- Verification started after all 14 hunters were recorded (no overlap).
- Re-asks: hunter-4 (unknown key `scope_note` in evidence), hunter-5 (one
  closing brace too many), hunter-8 / hunter-14 (`reviewed_paths` missing a
  check path), verifier-12 / verifier-15 (one trailing `}`), verifier-13
  (first: a rejected record without the required `description` and
  `evidence`; second: module-cache paths in evidence, refused by the digest).
  verifier-13 failed twice, so a fresh verifier-17 was launched per the rule
  (rejected, same conclusion).
- Self-reported shell use by Explore agents: hunter-14 (grep over
  schema.json), verifier-2 (grep over GOROOT), verifier-10 (grep over a class
  file), verifier-14 (ls / grep / sed / cat / `python3 -c`). All reported as
  read-only. Residual, already recorded in SKILL.md.

## Lessons → candidates for cut 8

| # | What happened | Proposed fix |
|---|---|---|
| E21 | The parent forgot `architecture.md` and wrote the context inline | `ledger.py brief` refuses when `RUN/architecture.md` is absent; `ledger.py architecture RUN` composes the Markdown from `agents/recon-*.json` (scripts keep the books) |
| E22 | The critic's and verifier's briefs show no `proposed_verdict` or root cause for a candidate (None) | `record` keeps the candidate's `proposed_verdict` and `root_cause` / `claimed_root_cause` in the queue and the briefs print them (SKILL.md already says they are there) |
| E23 | 3 of 36 first returns were malformed JSON (unbalanced braces) | On a save failure print 60 characters around the position so the re-ask can quote them (every re-ask that carried position and context succeeded first time) |
| E24 | A verifier dropped required fields of a rejected record, and cited files outside the target in evidence | The verifier contract states the required fields per verdict and that `trace` / `evidence` files are inside the target only, with dependency and standard-library citations in prose; `brief verifier` prints the required-field list from the schema |
| E25 | `estimate` still counts critics=1 after the critic launched and expects 17 candidates (16 pending) | Subtract launched critics; once hunting is over, use the real pending count |
| E26 | The cost gate was passed twice more mid-run (34 → 41 → 43) | Candidate rates split by profile: quick 0.43–0.48, standard 0.26 — per-profile constants (quick 0.45 / standard 0.30) and 15% re-asks; SKILL.md states that the gate is passed again only when the shortfall is certain |
| E27 | hunter-14, holding the whole-tree and secrets units, read 29 files for 186k | Assign a whole-tree unit alone to its hunter, and keep its `starting_paths` to the top of the tree |
| E28 | Three verifiers settled the hunter's blocker by reading GOROOT or the module cache (zoned answers, the `ResolveReference` branch, the htmlindex table) | The verifier contract allows reading the dependencies at the versions go.mod pins and GOROOT, cited in prose with the version |

The verifiers worked as designed: of the 8 candidates the hunters called
confirmed, 5 were confirmed (one narrowed first); of the 3 called
needs_validation, 1 stayed nv, 1 was confirmed (`<base href>`, settled by the
standard library source) and 1 was rejected. All 9 rejections were downgraded
to hardening notes.

## Estimate for the web-fetch standard run (with the E26 constants)

| Item | Rough figure |
|---|---|
| Units | 38 (the deferred one included) plus 2–3 added by critics |
| Carry-over | run-1's 6 confirmed and 1 needs_validation re-verified first; the 9 rejected suppress the same claims |
| Launches | 4 + hunter 13–14 + critic 3 + verifier 12–14 + reverifier 13–15 + 15% re-asks ≈ 55–60 |
| Tokens | about 5.5–6M |

## Adopted in cut (8) (2026-11-08)

E21–E28 all adopted (97 tests). E21–E26 in the scripts: `ledger.py architecture RUN`
composes `architecture.md` from `agents/recon-*.json` (refusing a return with an
absolute local path) and every `brief` refuses until it exists; the queue had kept the
hunter's proposal under `verdict`, so the briefs now present it as `proposed_verdict`
with the root cause; `brief verifier` prints `required_fields` per verdict and the
`file_rule` from the schema; `read_json` prints 60 characters around a failure; the
estimate subtracts launched critics, uses the real queue once hunting is over, and its
constants are quick 0.45 / standard 0.30 candidates per unit and 15% re-asks. E27
(whole-tree units alone with their hunter), E28 (reading pinned dependencies and GOROOT,
cited in prose) and the rule for passing the cost gate again (once, on a shortfall the
books show) are SKILL.md wording.
