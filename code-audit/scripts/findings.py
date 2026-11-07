#!/usr/bin/env python3
"""findings.json and notes.json of a code-audit run (stdlib only).

Usage:
    findings.py validate <run-dir | findings.json> [--target <dir>]
    findings.py add <run-dir> <record.json> [--replace] [--target <dir>]
    findings.py note <run-dir> --agent <id> --kind out_of_scope|hardening --text TEXT [--coverage-id ID]

`add` inserts one validated record, sorted by fingerprint, and refuses a
duplicate fingerprint unless --replace. The parent never rewrites
findings.json whole. With --target, the record's source digests are checked
against the current files so a stale record is refused.
"""

from __future__ import annotations

import argparse
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
    c.fail_if(validate_findings(run_dir, findings, target))
    c.emit({"ok": True, "records": len(findings), "verdicts": {v: sum(1 for r in findings if r.get("verdict") == v) for v in ledger.VERDICTS}})


def cmd_add(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    c.load_metadata(run_dir)
    rec = c.read_json(Path(args.record))
    if not isinstance(rec, dict):
        c.die("record must be an object")
    target = Path(args.target) if args.target else None
    errors = ledger.record_errors(run_dir, rec, "record")
    c.fail_if(errors)
    findings = c.load_findings(run_dir)
    existing = [i for i, r in enumerate(findings) if r.get("fingerprint") == rec["fingerprint"]]
    if existing and not args.replace:
        c.die(f"{rec['fingerprint']}: already in {c.FINDINGS_FILE}; pass --replace to replace it")
    replaced = None
    for i in reversed(existing):
        replaced = findings.pop(i)["verdict"]
    findings.append(rec)
    findings.sort(key=lambda r: r["fingerprint"])
    c.fail_if(validate_findings(run_dir, findings, target))
    c.write_json(run_dir / c.FINDINGS_FILE, findings)
    c.emit({"fingerprint": rec["fingerprint"], "verdict": rec["verdict"], "replaced": replaced, "records": len(findings)})


def cmd_note(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    c.load_metadata(run_dir)
    note = {"agent_id": args.agent, "kind": args.kind, "text": args.text}
    if args.coverage_id:
        note["coverage_id"] = args.coverage_id
    errors = c.validate_part(note, "note", "note")
    if not c.is_agent_id(args.agent):
        errors.append("note.agent_id: not a canonical agent id")
    c.fail_if(errors)
    notes = c.load_notes(run_dir)
    notes.append(note)
    c.save_notes(run_dir, notes)
    c.emit({"notes": len(notes)})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate")
    p.add_argument("path")
    p.add_argument("--target")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("add")
    p.add_argument("run_dir")
    p.add_argument("record")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--target")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("note")
    p.add_argument("run_dir")
    p.add_argument("--agent", required=True)
    p.add_argument("--kind", required=True, choices=["out_of_scope", "hardening"])
    p.add_argument("--text", required=True)
    p.add_argument("--coverage-id")
    p.set_defaults(func=cmd_note)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
