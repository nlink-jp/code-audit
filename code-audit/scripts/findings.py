#!/usr/bin/env python3
"""findings.json and notes.json of a code-audit run (stdlib only).

Usage:
    findings.py validate <run-dir | findings.json> [--target <dir>]
    findings.py add <run-dir> <record.json> [--replace --by <agent> [--confirmed-by <agent>]] [--target <dir>]
    findings.py digest <record.json | hunter-result.json | verifier-return.json> --target <dir>
    findings.py note <run-dir> --agent <id> --kind out_of_scope|hardening|lead|documentation --text TEXT [--coverage-id ID]
    findings.py accept <run-dir> --fingerprint <fp> --record <ADR or document> --reason TEXT [--date YYYY-MM-DD] [--withdraw]

`add` takes a record, or a verifier's whole return (its `record` is used),
and inserts one validated record, sorted by fingerprint, for a claim the
ledger holds (a pending candidate; with --replace, a decided one), and
refuses a duplicate fingerprint unless --replace. A replacement needs --by;
one that strengthens the verdict, severity, confidence or evidence kind also
needs --confirmed-by (a different agent). The parent never rewrites
findings.json whole. With --target, the record's source digests are checked
against the current files so a stale record is refused. `digest` fills
source_digests from the files a record cites, so the parent never computes
one by hand. `validate <run-dir>` also cross-checks the records against the
ledger's decisions. A new confirmed record also answers `path_actor` (whose
act makes the path happen) and `specified_in` (the record that decided the
behaviour, or `none`); one whose path the operator composes and whose
behaviour a record decided is not a finding (rule 3) and is refused. `accept`
is the owner's triage after the run: it logs that a confirmed finding is
accepted as it stands, with the record that says so, in dispositions.json;
the next run's `seed --prior` neither re-verifies nor re-reports it while
its sources are unchanged. `--withdraw` logs the reversal; the log is
append-only and the latest entry wins.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _contract as c  # noqa: E402
import ledger  # noqa: E402  (record_errors is the one definition of a record's bar)


def validate_findings(run_dir: Path | None, findings: list, target: Path | None) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    for i, rec in enumerate(findings):
        base = f"findings[{i}]"
        if not isinstance(rec, dict):
            errors.append(f"{base}: expected object")
            continue
        errors += ledger.record_errors(run_dir, rec, base)
        if not errors and any(f in rec for f in ledger.NEW_CONFIRMED_FIELDS):
            # A record of this version is held to rule 3 on every validate;
            # a prior run's record (neither field) is read as it was written.
            errors += new_record_errors(rec, base)
        fp = rec.get("fingerprint")
        if isinstance(fp, str):
            if fp in seen:
                errors.append(f"{base}.fingerprint: duplicate of findings[{seen[fp]}]")
            seen[fp] = i
            if i > 0 and isinstance(findings[i - 1], dict) and str(findings[i - 1].get("fingerprint", "")) > fp:
                errors.append(f"{base}.fingerprint: records must be sorted lexicographically")
        if target is not None and isinstance(rec.get("source_digests"), dict):
            current = c.digests_for(target, rec["source_digests"].keys())
            stale = [k for k, v in rec["source_digests"].items() if current.get(k) != v]
            if stale:
                errors.append(f"{base}.source_digests: cited source changed since the record was written: {stale}")
    return errors


def cmd_validate(args: argparse.Namespace) -> None:
    path = Path(args.path)
    if path.is_dir():
        run_dir, findings = path, c.load_findings(path)
    else:
        run_dir, findings = None, c.read_json(path)
        if not isinstance(findings, list):
            c.die(f"{path}: expected a top-level array")
    target = Path(args.target) if args.target else None
    errors = validate_findings(run_dir, findings, target)
    if run_dir is not None and (run_dir / c.LEDGER_FILE).exists():
        errors += ledger.cross_check(findings, ledger.load_ledger(run_dir), c.load_candidates(run_dir))
    c.fail_if(errors)
    c.emit({"ok": True, "records": len(findings), "verdicts": {v: sum(1 for r in findings if r.get("verdict") == v) for v in ledger.VERDICTS}})


VERDICT_RANK = {"rejected": 0, "needs_validation": 1, "confirmed": 2}
LEVEL_RANK = {"informational": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
EVIDENCE_RANK = {"source": 0, "existing_test": 1}


def strengthened_fields(old: dict, new: dict) -> list[str]:
    """The fields along which `new` claims more than `old` did.

    The replacement rule (RFP §3): a re-verifier's replacement that keeps or
    weakens the verdict, severity or confidence — or only corrects wording and
    line numbers — is applied directly; one that strengthens any of them is
    confirmed by another fresh verifier first. Prose fields (root cause,
    description) cannot be ranked here; the workflow treats a widened root
    cause as strengthening and passes --confirmed-by for it."""
    out: list[str] = []
    if VERDICT_RANK[new["verdict"]] > VERDICT_RANK[old["verdict"]]:
        out.append("verdict")
    if old["verdict"] == "confirmed" and new["verdict"] == "confirmed":
        for path, rank in (
            (("severity", "overall"), LEVEL_RANK),
            (("severity", "impact", "score"), LEVEL_RANK),
            (("severity", "likelihood", "score"), LEVEL_RANK),
            (("confidence", "score"), LEVEL_RANK),
            (("evidence_kind",), EVIDENCE_RANK),
        ):
            o, n = old, new
            for k in path:
                o, n = o[k], n[k]
            if rank[n] > rank[o]:
                out.append(".".join(path))
    return out


def weakened_fields(old: dict, new: dict) -> list[str]:
    """The fields along which `new` claims less than `old` did (E35: the
    report says so instead of calling every unstrengthened replacement a
    wording fix)."""
    return strengthened_fields(new, old)


def cmd_add(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    c.load_metadata(run_dir)
    rec = c.read_json(Path(args.record))
    if isinstance(rec, dict) and isinstance(rec.get("record"), dict):
        rec = rec["record"]  # a verifier's or re-verifier's whole return
    if not isinstance(rec, dict):
        c.die("record must be an object")
    target = Path(args.target) if args.target else None
    errors = ledger.record_errors(run_dir, rec, "record") + c.personal_identifier_errors(rec, "record")
    if not errors:
        errors += new_record_errors(rec, "record")
    c.fail_if(errors)
    findings = c.load_findings(run_dir)
    existing = [i for i, r in enumerate(findings) if r.get("fingerprint") == rec["fingerprint"]]
    if existing and not args.replace:
        c.die(f"{rec['fingerprint']}: already in {c.FINDINGS_FILE}; pass --replace to replace it")
    if args.replace and not existing:
        c.die(f"{rec['fingerprint']}: nothing to replace; it is not in {c.FINDINGS_FILE}")
    if (run_dir / c.LEDGER_FILE).exists():
        # A record enters only for a claim the ledger holds: a pending
        # candidate (first add) or a decided one (replacement), citing units
        # that exist. Otherwise a never-hunted claim would reach the report.
        units = ledger.load_ledger(run_dir)
        cands = c.load_candidates(run_dir)
        ids = {u["coverage_id"] for u in units}
        fp = rec["fingerprint"]
        missing = [cid for cid in rec["coverage_ids"] if cid not in ids]
        if missing:
            c.die(f"{fp}: coverage ids not in the ledger: {missing}")
        queued = {r["fingerprint"]: r for key in ("candidates", "carried") for r in cands[key]}
        pending = set(queued)
        decided = {d["fingerprint"] for d in cands["decided"]}
        if not existing and fp not in pending:
            c.die(f"{fp}: not a pending candidate of this run; a record needs a claim the ledger holds")
        if not existing and set(queued[fp].get("coverage_ids", [])) != set(rec["coverage_ids"]):
            c.die(f"{fp}: the record's coverage_ids must be the queued candidate's: {sorted(queued[fp].get('coverage_ids', []))}")
        if existing and fp not in decided:
            c.die(f"{fp}: the record exists but was never decided; run ledger.py decide before replacing it")
    replaced = None
    entry = None
    if existing:
        old = findings[existing[-1]]
        if set(old.get("coverage_ids", [])) != set(rec["coverage_ids"]):
            c.die(f"{rec['fingerprint']}: a replacement keeps the record's coverage_ids")
        if not args.by or not c.is_agent_id(args.by):
            c.die("--replace needs --by <agent-id> (the re-verifier that wrote the replacement)")
        strengthened = strengthened_fields(old, rec)
        if args.confirmed_by is not None and (not c.is_agent_id(args.confirmed_by) or args.confirmed_by == args.by):
            c.die("--confirmed-by must be a canonical agent id different from --by")
        if strengthened and not args.confirmed_by:
            c.die(f"{rec['fingerprint']}: the replacement strengthens {', '.join(strengthened)}; a different fresh verifier must confirm it (--confirmed-by <agent-id>)")
        entry = {
            "fingerprint": rec["fingerprint"],
            "previous_verdict": old["verdict"],
            "verdict": rec["verdict"],
            "strengthened": strengthened,
            "weakened": weakened_fields(old, rec),
            "by": args.by,
            "confirmed_by": args.confirmed_by,
        }
    for i in reversed(existing):
        replaced = findings.pop(i)["verdict"]
    findings.append(rec)
    findings.sort(key=lambda r: r["fingerprint"])
    c.fail_if(validate_findings(run_dir, findings, target))
    c.write_json(run_dir / c.FINDINGS_FILE, findings)
    if entry is not None:
        items = c.load_replacements(run_dir)
        items.append(entry)
        c.save_replacements(run_dir, items)
    c.emit({
        "fingerprint": rec["fingerprint"],
        "verdict": rec["verdict"],
        "replaced": replaced,
        "strengthened": entry["strengthened"] if entry else [],
        "weakened": entry["weakened"] if entry else [],
        "verdict_changed": bool(entry) and entry["previous_verdict"] != rec["verdict"],
        "records": len(findings),
    })


SPECIFIED_NONE = "none"


def new_record_errors(rec: dict, where: str) -> list[str]:
    """What a record written by this version must answer beyond the schema
    (E37, gem-agent audit 2026-11-09): whose act makes the path happen, and
    which record decided the behaviour. A prior run's records are read
    without these, so the schema keeps them optional and only `add` insists.
    Rule 3 of references/severity.md: a path the operator composes, whose
    behaviour a record decided, is not a finding — the verifier returns
    `rejected` naming the record, and a `documentation` note when the record
    is not stated where the operator reads."""
    if rec.get("verdict") != "confirmed":
        return []
    errors = [f"{where}.{f}: a new confirmed record answers it (see required_fields in the brief)" for f in ledger.NEW_CONFIRMED_FIELDS if f not in rec]
    if errors:
        return errors
    if rec["path_actor"] == "operator_composed" and rec["specified_in"].strip().lower() != SPECIFIED_NONE:
        errors.append(f"{where}: not a finding (references/severity.md rule 3) — the path needs the operator's own act and {rec['specified_in']} decided the behaviour; return rejected with a reason naming that record, and a documentation note if it is not stated where the operator reads")
    return errors


def cited_files(rec: dict) -> list[str]:
    files = {t.get("file") for t in rec.get("trace", []) if isinstance(t, dict)}
    files |= {e.get("file") for e in rec.get("evidence", []) if isinstance(e, dict)}
    return sorted(f for f in files if isinstance(f, str) and f)


def cmd_digest(args: argparse.Namespace) -> None:
    """Fill `source_digests` of a record, of every candidate in a hunter
    result, or of the `record` in a verifier return, from the files its trace
    and evidence cite, and write the file back. The parent never computes a
    digest by hand."""
    path = Path(args.path)
    data = c.read_json(path)
    target = Path(args.target)
    if not target.is_dir():
        c.die(f"target is not a directory: {args.target}")
    if not isinstance(data, dict):
        c.die("expected a JSON object")
    if isinstance(data.get("candidates"), list):
        records = [r for r in data["candidates"] if isinstance(r, dict)]
    elif isinstance(data.get("record"), dict):
        records = [data["record"]]
    else:
        records = [data]
    filled = {}
    for rec in records:
        files = cited_files(rec)
        if not files:
            continue
        rec["source_digests"] = c.digests_for(target, files)
        filled[rec.get("fingerprint", "?")] = rec["source_digests"]
    c.write_json(path, data)
    c.emit({"path": str(path.name), "digested": filled})


def cmd_note(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    c.load_metadata(run_dir)
    note = {"agent_id": args.agent, "kind": args.kind, "text": args.text}
    if args.coverage_id:
        note["coverage_id"] = args.coverage_id
    errors = c.validate_part(note, "note", "note") + c.forbidden_char_errors(note, "note") + c.personal_identifier_errors(note, "note")
    if not c.is_agent_id(args.agent):
        errors.append("note.agent_id: not a canonical agent id")
    c.fail_if(errors)
    notes = c.load_notes(run_dir)
    notes.append(note)
    c.save_notes(run_dir, notes)
    c.emit({"notes": len(notes)})


def cmd_accept(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    c.load_metadata(run_dir)
    kind = "withdrawn" if args.withdraw else "accepted"
    entry = {"fingerprint": args.fingerprint, "kind": kind, "record": args.record, "reason": args.reason, "date": args.date or _dt.date.today().isoformat()}
    errors = c.validate_part(entry, "disposition", "disposition") + c.forbidden_char_errors(entry, "disposition") + c.personal_identifier_errors(entry, "disposition")
    if not errors:
        try:
            _dt.date.fromisoformat(entry["date"])
        except ValueError:
            errors.append(f"disposition.date: {entry['date']} is not a calendar date")
    c.fail_if(errors)
    findings = c.load_findings(run_dir)
    rec = next((r for r in findings if r.get("fingerprint") == args.fingerprint), None)
    if rec is None:
        c.die(f"{args.fingerprint}: not in {c.FINDINGS_FILE}; only a record of this run can be accepted")
    if rec.get("verdict") != "confirmed":
        c.die(f"{args.fingerprint}: is {rec.get('verdict')}; only a confirmed finding is accepted (a lead is settled by validation, a rejected claim needs nothing)")
    decided = {d["fingerprint"] for d in c.load_candidates(run_dir)["decided"]}
    if (run_dir / c.LEDGER_FILE).exists() and args.fingerprint not in decided:
        c.die(f"{args.fingerprint}: the ledger never decided it; run ledger.py decide first")
    items = c.load_dispositions(run_dir)
    current = c.accepted_dispositions(items)
    if kind == "accepted" and args.fingerprint in current:
        c.die(f"{args.fingerprint}: already accepted ({current[args.fingerprint]['record']}, {current[args.fingerprint]['date']}); pass --withdraw to reverse it")
    if kind == "withdrawn" and args.fingerprint not in current:
        c.die(f"{args.fingerprint}: not accepted; nothing to withdraw")
    items.append(entry)
    c.save_dispositions(run_dir, items)
    c.emit({"fingerprint": args.fingerprint, "kind": kind, "record": args.record, "accepted": sorted(c.accepted_dispositions(items))})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.add_argument("path")
    p.add_argument("--target")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("digest")
    p.add_argument("path")
    p.add_argument("--target", required=True)
    p.set_defaults(func=cmd_digest)

    p = sub.add_parser("add")
    p.add_argument("run_dir")
    p.add_argument("record")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--by", help="agent id of the re-verifier whose replacement this is (required with --replace)")
    p.add_argument("--confirmed-by", help="agent id of the fresh verifier that confirmed a strengthening replacement")
    p.add_argument("--target")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("note")
    p.add_argument("run_dir")
    p.add_argument("--agent", required=True)
    p.add_argument("--kind", required=True, choices=["out_of_scope", "hardening", "lead", "documentation"])
    p.add_argument("--text", required=True)
    p.add_argument("--coverage-id")
    p.set_defaults(func=cmd_note)

    p = sub.add_parser("accept")
    p.add_argument("run_dir")
    p.add_argument("--fingerprint", required=True)
    p.add_argument("--record", required=True, help="the decision record that accepts the behaviour, e.g. ADR-0113 or docs/en/reference/approval.md")
    p.add_argument("--reason", required=True)
    p.add_argument("--date", help="YYYY-MM-DD; today when omitted")
    p.add_argument("--withdraw", action="store_true", help="log that an earlier acceptance is reversed")
    p.set_defaults(func=cmd_accept)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
