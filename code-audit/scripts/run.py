#!/usr/bin/env python3
"""Run metadata and bounded execution for a code-audit run (stdlib only).

Usage:
    run.py init --target <dir> [--output <dir>] [--profile quick|standard]
                [--budget N] [--prior <run-dir>]...
    run.py set-budget <run-dir> N
    run.py count <run-dir> reconnaissance|hunter|critic|verifier|reverifier [--n N]
    run.py set-status <run-dir> complete|incomplete [--reason TEXT]
    run.py validate <run-dir>
    run.py exec <run-dir> <command-id> --target <dir>

`init` creates the output directory (default ~/code-audit-runs/<repo>/run-N),
refuses one inside the target by resolved-path comparison, and writes
run-metadata.json — the repo name from the git remote, never the checkout
path. `exec` runs only a command that commands.json lists as allowed, from an
empty environment plus the entry's allowlisted variables, inside the target,
with a time limit, and writes the record to checks/<id>.log. It cannot block
the network: a command that reaches it is forbidden in the ledger instead.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _contract as c  # noqa: E402

ROLES = ("reconnaissance", "hunter", "critic", "verifier", "reverifier")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


def git(target: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(target), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def repo_name(target: Path) -> str:
    url = git(target, "remote", "get-url", "origin")
    if url:
        m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
        if m:
            return f"{m.group(1)}/{m.group(2)}"
    return target.resolve().name


def next_run_dir(base: Path) -> Path:
    n = 1
    while (base / f"run-{n}").exists():
        n += 1
    return base / f"run-{n}"


def cmd_init(args: argparse.Namespace) -> None:
    target = Path(args.target)
    if not target.is_dir():
        c.die(f"target is not a directory: {args.target}")
    name = repo_name(target)
    run_dir = Path(args.output) if args.output else next_run_dir(Path.home() / "code-audit-runs" / name.replace("/", "__"))
    if c.is_inside(run_dir, target):
        c.die("output directory is inside the target; choose a directory outside the repository under audit")
    if c.is_inside(target, run_dir):
        c.die("the target is inside the output directory; choose a separate directory")
    if run_dir.exists() and any(run_dir.iterdir()):
        c.die(f"output directory exists and is not empty: {args.output}")
    priors: list[str] = []
    for p in args.prior or []:
        pp = Path(p)
        if not (pp / c.METADATA_FILE).is_file():
            c.die(f"prior run has no {c.METADATA_FILE}: {p}")
        priors.append(pp.resolve().name)
    source_ref = git(target, "rev-parse", "HEAD")
    porcelain = git(target, "status", "--porcelain")
    if source_ref is None:
        source_ref, dirty = "unversioned", True
    else:
        dirty = bool(porcelain)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / c.CHECKS_DIR).mkdir(exist_ok=True)
    metadata = {
        "run_id": run_dir.name if re.match(r"^run-[0-9]+$", run_dir.name) else re.sub(r"[^a-z0-9_-]", "-", run_dir.name.lower())[:64] or "run",
        "repo": name,
        "source_ref": source_ref,
        "dirty": dirty,
        "profile": args.profile,
        "budget": args.budget,
        "prior_runs": priors,
        "invocations": {r: 0 for r in ROLES},
        "run_status": "in_progress",
        "incomplete_reason": None,
        "created": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "execution_policy": "read-and-existing-tests",
    }
    c.fail_if(c.validate_part(metadata, "metadata"))
    c.write_json(run_dir / c.METADATA_FILE, metadata)
    c.emit({"output_dir": str(run_dir), "run_id": metadata["run_id"], "repo": name, "source_ref": source_ref, "dirty": dirty, "profile": args.profile})


# ---------------------------------------------------------------------------
# metadata updates
# ---------------------------------------------------------------------------


def cmd_set_budget(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    meta = c.load_metadata(run_dir)
    if args.n < 1:
        c.die("budget must be a positive integer")
    meta["budget"] = args.n
    c.write_json(run_dir / c.METADATA_FILE, meta)
    c.emit({"budget": meta["budget"]})


def cmd_count(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    meta = c.load_metadata(run_dir)
    meta["invocations"][args.role] += args.n
    total = sum(meta["invocations"].values())
    over = meta["budget"] is not None and total > meta["budget"]
    c.write_json(run_dir / c.METADATA_FILE, meta)
    c.emit({"invocations": meta["invocations"], "total": total, "budget": meta["budget"], "over_budget": over})
    if over:
        print("WARNING: invocations exceed the recorded budget", file=sys.stderr)


def cmd_set_status(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    meta = c.load_metadata(run_dir)
    if args.status == "incomplete" and not args.reason:
        c.die("incomplete needs --reason")
    meta["run_status"] = args.status
    meta["incomplete_reason"] = args.reason if args.status == "incomplete" else None
    c.write_json(run_dir / c.METADATA_FILE, meta)
    c.emit({"run_status": meta["run_status"], "incomplete_reason": meta["incomplete_reason"]})


def cmd_validate(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    errors: list[str] = []
    meta = c.read_json(run_dir / c.METADATA_FILE)
    errors += c.validate_part(meta, "metadata", "run-metadata")
    commands_path = run_dir / c.COMMANDS_FILE
    if commands_path.exists():
        errors += validate_commands(c.read_json(commands_path))
    c.fail_if(errors)
    c.emit({"ok": True, "commands": commands_path.exists()})


# ---------------------------------------------------------------------------
# exec
# ---------------------------------------------------------------------------


def validate_commands(data: object) -> list[str]:
    errors = c.validate_part(data, "commands", "commands")
    if errors:
        return errors
    seen: set[str] = set()
    for i, entry in enumerate(data["commands"]):  # type: ignore[index]
        base = f"commands.commands[{i}]"
        if entry["id"] in seen:
            errors.append(f"{base}.id: duplicate id '{entry['id']}'")
        seen.add(entry["id"])
        if not entry["allowed"] and not entry["reason"].strip():
            errors.append(f"{base}.reason: a forbidden command needs a reason")
        if entry["cwd"] != "." and not c.is_repo_relative(entry["cwd"]):
            errors.append(f"{base}.cwd: must be '.' or a repository-relative path")
        for w in entry["writes"]:
            if not c.is_repo_relative(w):
                errors.append(f"{base}.writes: '{w}' must be repository-relative")
    return errors


def cmd_exec(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    target = Path(args.target)
    if not target.is_dir():
        c.die(f"target is not a directory: {args.target}")
    c.load_metadata(run_dir)
    commands = c.read_json(run_dir / c.COMMANDS_FILE)
    c.fail_if(validate_commands(commands))
    entry = next((e for e in commands["commands"] if e["id"] == args.command_id), None)  # type: ignore[index]
    if entry is None:
        c.die(f"command '{args.command_id}' is not in {c.COMMANDS_FILE}; only ledger commands run")
    if not entry["allowed"]:
        c.die(f"command '{args.command_id}' is forbidden: {entry['reason']}")
    cwd = target if entry["cwd"] == "." else target / entry["cwd"]
    if not c.is_inside(cwd, target) or not cwd.is_dir():
        c.die(f"command cwd escapes the target or does not exist: {entry['cwd']}")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
    for name in entry["env_allow"]:
        if name in os.environ:
            env[name] = os.environ[name]
    log_path = run_dir / c.CHECKS_DIR / f"{entry['id']}.log"
    log_path.parent.mkdir(exist_ok=True)
    started = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(entry["argv"], cwd=str(cwd), env=env, capture_output=True, text=True, timeout=entry["timeout_sec"], errors="replace")
        exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out, exit_code = True, None
        stdout = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    except OSError as exc:
        exit_code, stdout, stderr = None, "", f"could not start: {exc}"
    duration = round(time.monotonic() - started, 3)
    header = [
        f"command_id: {entry['id']}",
        f"argv: {entry['argv']}",
        f"cwd: {entry['cwd']}",
        f"env_allow: {sorted(env)}",
        f"timeout_sec: {entry['timeout_sec']}",
        f"timed_out: {timed_out}",
        f"exit_code: {exit_code}",
        f"duration_sec: {duration}",
        f"source: {entry['source']}",
        "",
        "--- stdout ---",
        stdout.rstrip("\n"),
        "--- stderr ---",
        stderr.rstrip("\n"),
        "",
    ]
    log_path.write_text("\n".join(header), encoding="utf-8")
    c.emit({"check_log": f"{c.CHECKS_DIR}/{entry['id']}.log", "exit_code": exit_code, "timed_out": timed_out, "duration_sec": duration})


# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--target", required=True)
    p.add_argument("--output")
    p.add_argument("--profile", choices=["quick", "standard"], default="standard")
    p.add_argument("--budget", type=int)
    p.add_argument("--prior", action="append")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("set-budget")
    p.add_argument("run_dir")
    p.add_argument("n", type=int)
    p.set_defaults(func=cmd_set_budget)

    p = sub.add_parser("count")
    p.add_argument("run_dir")
    p.add_argument("role", choices=ROLES)
    p.add_argument("--n", type=int, default=1)
    p.set_defaults(func=cmd_count)

    p = sub.add_parser("set-status")
    p.add_argument("run_dir")
    p.add_argument("status", choices=["complete", "incomplete"])
    p.add_argument("--reason")
    p.set_defaults(func=cmd_set_status)

    p = sub.add_parser("validate")
    p.add_argument("run_dir")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("exec")
    p.add_argument("run_dir")
    p.add_argument("command_id")
    p.add_argument("--target", required=True)
    p.set_defaults(func=cmd_exec)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
