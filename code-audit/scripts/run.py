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
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _contract as c  # noqa: E402

ROLES = ("reconnaissance", "hunter", "critic", "verifier", "reverifier")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


# The target is untrusted input. Its .git/config may name commands (a
# fsmonitor, a clean filter that `git status` runs on a touched file, hooks,
# an ssh command), and -c overrides cannot undefine a filter the repository
# defines. So git never sees the target's config: `init` copies HEAD, the
# index, refs and exclude data into a scratch git-dir with a minimal config
# of its own, links the object store, and runs git against that.

GIT_HARDENING = [
    "-c", "core.fsmonitor=false",
    "-c", "core.untrackedCache=false",
    "-c", "core.hooksPath=/dev/null",
    "-c", "core.sshCommand=/usr/bin/false",
    "-c", "core.pager=cat",
    "-c", "protocol.allow=never",
]
GIT_ENV = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_OPTIONAL_LOCKS": "0",
    "LC_ALL": "C",
}
# Repository config keys copied into the scratch config: data that changes
# how the index is compared, never a command. Values are checked against the
# pattern before they are written.
CONFIG_COPY = {
    "core.filemode": r"^(true|false)$",
    "core.ignorecase": r"^(true|false)$",
    "core.precomposeunicode": r"^(true|false)$",
    "core.symlinks": r"^(true|false)$",
    "core.autocrlf": r"^(true|false|input)$",
    "extensions.objectformat": r"^(sha1|sha256)$",
    "extensions.refstorage": r"^(files|reftable)$",
}


def parse_git_config(text: str) -> dict[str, str]:
    """Flat `section[.subsection].key -> value` map of a git config file.
    Read as text only; nothing in it is ever passed to git."""
    out: dict[str, str] = {}
    section: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        m = re.match(r'^\[([^\s"\]]+)(?:\s+"((?:[^"\\]|\\.)*)")?\]$', line)
        if m:
            section = m.group(1).lower() + (f".{m.group(2)}" if m.group(2) else "")
            continue
        if section and "=" in line:
            key, value = line.split("=", 1)
            out[f"{section}.{key.strip().lower()}"] = value.strip()
    return out


def resolve_git_dir(target: Path) -> tuple[Path, Path] | None:
    """(git-dir, common-dir) of the target, following a `gitdir:` file
    (linked worktree or submodule) and a `commondir` file one level."""
    dot = target / ".git"
    if dot.is_dir():
        gitdir = dot
    elif dot.is_file():
        line = dot.read_text(encoding="utf-8", errors="replace").strip()
        if not line.startswith("gitdir:"):
            return None
        gitdir = (target / line[len("gitdir:"):].strip()).resolve()
        if not gitdir.is_dir():
            return None
    else:
        return None
    common = gitdir
    cd = gitdir / "commondir"
    if cd.is_file():
        common = (gitdir / cd.read_text(encoding="utf-8", errors="replace").strip()).resolve()
    return gitdir, common


def sanitized_git_dir(gitdir: Path, common: Path, scratch: Path) -> dict[str, str] | None:
    """Build a git-dir under scratch that holds the target's HEAD, index,
    refs, packed-refs, shallow list and ignore data, links its object store,
    and carries a config of our own. Returns the parsed original config."""
    head = gitdir / "HEAD"
    if not head.is_file():
        return None
    shutil.copy(head, scratch / "HEAD")
    if (gitdir / "index").is_file():
        shutil.copy(gitdir / "index", scratch / "index")
    for name in ("packed-refs", "shallow"):
        if (common / name).is_file():
            shutil.copy(common / name, scratch / name)
    for name in ("refs", "reftable"):
        if (common / name).is_dir():
            shutil.copytree(common / name, scratch / name, symlinks=False)
    (scratch / "refs").mkdir(exist_ok=True)
    if (common / "info" / "exclude").is_file():
        (scratch / "info").mkdir()
        shutil.copy(common / "info" / "exclude", scratch / "info" / "exclude")
    os.symlink(common / "objects", scratch / "objects")
    config_path = common / "config"
    original = parse_git_config(config_path.read_text(encoding="utf-8", errors="replace")) if config_path.is_file() else {}
    copied = {k: v for k, v in original.items() if k in CONFIG_COPY and re.match(CONFIG_COPY[k], v)}
    version = "1" if any(k.startswith("extensions.") for k in copied) else "0"
    lines = ["[core]", f"\trepositoryformatversion = {version}", "\tbare = false"]
    lines += [f"\t{k.split('.', 1)[1]} = {v}" for k, v in copied.items() if k.startswith("core.")]
    if version == "1":
        lines.append("[extensions]")
        lines += [f"\t{k.split('.', 1)[1]} = {v}" for k, v in copied.items() if k.startswith("extensions.")]
    (scratch / "config").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return original


def git(scratch: Path, worktree: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", *GIT_HARDENING, "--git-dir", str(scratch), "--work-tree", str(worktree), *args], capture_output=True, text=True, timeout=60, env=GIT_ENV)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def repo_name_from(config: dict[str, str], target: Path) -> str:
    url = config.get("remote.origin.url", "")
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    return target.resolve().name


def inspect_target(target: Path) -> dict:
    """repo name, source ref and dirty flag without letting the target's
    git config reach git. A target without a usable .git is 'unversioned'."""
    resolved = resolve_git_dir(target)
    if resolved is None:
        return {"repo": target.resolve().name, "source_ref": "unversioned", "dirty": True}
    gitdir, common = resolved
    with tempfile.TemporaryDirectory(prefix="code-audit-git-") as tmp:
        scratch = Path(tmp) / "gitdir"
        scratch.mkdir()
        original = sanitized_git_dir(gitdir, common, scratch)
        if original is None:
            return {"repo": target.resolve().name, "source_ref": "unversioned", "dirty": True}
        name = repo_name_from(original, target)
        source_ref = git(scratch, target, "rev-parse", "HEAD")
        porcelain = git(scratch, target, "status", "--porcelain", "--no-renames", "--ignore-submodules=all")
    if source_ref is None or porcelain is None:
        return {"repo": name, "source_ref": "unversioned", "dirty": True}
    return {"repo": name, "source_ref": source_ref, "dirty": bool(porcelain)}


def next_run_dir(base: Path) -> Path:
    n = 1
    while (base / f"run-{n}").exists():
        n += 1
    return base / f"run-{n}"


def cmd_init(args: argparse.Namespace) -> None:
    target = Path(args.target)
    if not target.is_dir():
        c.die(f"target is not a directory: {args.target}")
    info = inspect_target(target)
    name = info["repo"]
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
    source_ref, dirty = info["source_ref"], info["dirty"]
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
        # A new session puts the command and every process it spawns in one
        # process group, so a timeout kills the group: killing only the
        # direct child would leave grandchildren holding the pipes open.
        proc = subprocess.Popen(entry["argv"], cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            out_b, err_b = proc.communicate(timeout=entry["timeout_sec"])
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out, exit_code = True, None
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                out_b, err_b = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                out_b, err_b = b"", b""
        stdout = out_b.decode("utf-8", "replace")
        stderr = err_b.decode("utf-8", "replace")
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
