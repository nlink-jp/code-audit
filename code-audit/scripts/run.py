#!/usr/bin/env python3
"""Run metadata and bounded execution for a code-audit run (stdlib only).

Usage:
    run.py init --target <dir> [--output <dir>] [--profile quick|standard]
    run.py approve <run-dir> [--budget N]
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
import signal
import stat
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


def points_back_at(gitdir: Path, target: Path) -> bool:
    """Whether a git-dir outside the target is the target's own: a linked
    worktree's `<common>/worktrees/<name>` (its `gitdir` file names the
    target's `.git`) or a submodule's `<super>/.git/modules/<name>` (its
    config's core.worktree resolves to the target). Anything else is another
    repository the target merely points at."""
    wt = gitdir / "gitdir"
    if wt.is_file():
        named = Path(wt.read_text(encoding="utf-8", errors="replace").strip())
        if named.name == ".git" and c.same_place(named.parent, target):
            return True
    cfg = gitdir / "config"
    if cfg.is_file():
        worktree = parse_git_config(cfg.read_text(encoding="utf-8", errors="replace")).get("core.worktree")
        if worktree and c.same_place(gitdir / worktree, target):
            return True
    return False


def resolve_git_dir(target: Path) -> tuple[Path, Path] | None:
    """(git-dir, common-dir) of the target, following a `gitdir:` file
    (linked worktree or submodule) and a `commondir` file one level. A
    `.git` that is a link, or a git-dir outside the target that does not
    point back at it, makes the target `unversioned`: the target must not be
    able to lend another repository's name and history to the run."""
    dot = target / ".git"
    if dot.is_symlink():
        return None
    if dot.is_dir():
        gitdir = dot
    elif dot.is_file():
        line = dot.read_text(encoding="utf-8", errors="replace").strip()
        if not line.startswith("gitdir:"):
            return None
        gitdir = (target / line[len("gitdir:"):].strip()).resolve()
        if not gitdir.is_dir():
            return None
        if not c.is_inside(gitdir, target) and not points_back_at(gitdir, target):
            return None
    else:
        return None
    common = gitdir
    cd = gitdir / "commondir"
    if cd.is_file():
        common = (gitdir / cd.read_text(encoding="utf-8", errors="replace").strip()).resolve()
        if not c.is_inside(common, target) and not c.is_inside(gitdir, common):
            return None
    return gitdir, common


# Bounds for the copy into the scratch git-dir: the target may plant a
# symlink to a device or a huge file under .git, so only regular files are
# copied, never through a link, and never past these totals.
COPY_LIMITS = {"bytes": 512 * 1024 * 1024, "files": 200_000, "file_bytes": 512 * 1024 * 1024, "depth": 32}


class CopyBudgetExceeded(OSError):
    pass


def copy_regular_file(src: Path, dst: Path, budget: dict[str, int]) -> bool:
    """Copy src to dst if src is a regular file reached without following a
    link; charge the budget. Returns False when src is not such a file."""
    try:
        fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return False
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return False
        if st.st_size > budget["file_bytes"] or st.st_size > budget["bytes"] or budget["files"] < 1:
            raise CopyBudgetExceeded(f"{src}: exceeds the git-dir copy budget")
        remaining = st.st_size
        with open(os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as out:
            while remaining > 0:
                chunk = os.read(fd, min(1 << 20, remaining))
                if not chunk:
                    break
                out.write(chunk)
                remaining -= len(chunk)
        budget["bytes"] -= st.st_size
        budget["files"] -= 1
        return True
    finally:
        os.close(fd)


def copy_regular_tree(src: Path, dst: Path, budget: dict[str, int], depth: int = 0) -> None:
    """Copy the regular files under src, skipping symlinks and special files.
    Every entry, directories included, is charged to the file budget, and
    nesting past COPY_LIMITS['depth'] exceeds the budget."""
    if depth > COPY_LIMITS["depth"]:
        raise CopyBudgetExceeded(f"{src}: nesting exceeds the git-dir copy budget")
    dst.mkdir()
    with os.scandir(src) as it:
        for entry in it:
            if budget["files"] < 1:
                raise CopyBudgetExceeded(f"{entry.path}: exceeds the git-dir copy budget")
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                budget["files"] -= 1
                copy_regular_tree(Path(entry.path), dst / entry.name, budget, depth + 1)
            elif entry.is_file(follow_symlinks=False):
                copy_regular_file(Path(entry.path), dst / entry.name, budget)


def sanitized_git_dir(gitdir: Path, common: Path, scratch: Path) -> dict[str, str] | None:
    """Build a git-dir under scratch that holds the target's HEAD, index,
    refs, packed-refs, shallow list and ignore data, links its object store,
    and carries a config of our own. Returns the parsed original config, or
    None when the target's git-dir is unusable or exceeds the copy budget."""
    budget = dict(COPY_LIMITS)
    try:
        if not copy_regular_file(gitdir / "HEAD", scratch / "HEAD", budget):
            return None
        copy_regular_file(gitdir / "index", scratch / "index", budget)
        for name in ("packed-refs", "shallow"):
            copy_regular_file(common / name, scratch / name, budget)
        for name in ("refs", "reftable"):
            if (common / name).is_dir() and not (common / name).is_symlink():
                copy_regular_tree(common / name, scratch / name, budget)
        (scratch / "refs").mkdir(exist_ok=True)
        if (common / "info").is_dir() and not (common / "info").is_symlink():
            (scratch / "info").mkdir()
            copy_regular_file(common / "info" / "exclude", scratch / "info" / "exclude", budget)
        os.symlink(common / "objects", scratch / "objects")
        config_path = common / "config"
        original: dict[str, str] = {}
        if config_path.is_file() and not config_path.is_symlink() and config_path.stat().st_size <= 1 << 20:
            original = parse_git_config(config_path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, RecursionError):
        return None
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


NAME_PART_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def repo_name_from(config: dict[str, str], target: Path) -> str:
    """owner/name from the remote URL when both parts have the shape of a
    repository name; otherwise the target directory's name, reduced to that
    shape. The URL is the target's text and becomes a title and a directory
    name, so it is accepted by shape, never by trust."""
    url = config.get("remote.origin.url", "")
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    if m and NAME_PART_RE.fullmatch(m.group(1)) and NAME_PART_RE.fullmatch(m.group(2)) and m.group(1) not in (".", "..") and m.group(2) not in (".", ".."):
        return f"{m.group(1)}/{m.group(2)}"
    base = re.sub(r"[^A-Za-z0-9._-]", "-", target.resolve().name)[:100].strip(".-")
    return base or "target"


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
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / c.CHECKS_DIR).mkdir(exist_ok=True)
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


def cmd_approve(args: argparse.Namespace) -> None:
    """Record the human's approval of the cost estimate. Until it is recorded
    no hunter can be assigned (`ledger.py assign` checks it); the budget is
    the one given here, else the one already recorded, else the estimate's
    total."""
    run_dir = Path(args.run_dir)
    meta = c.load_metadata(run_dir)
    if args.budget is not None:
        if args.budget < 1:
            c.die("budget must be a positive integer")
        meta["budget"] = args.budget
    if meta["budget"] is None:
        if not (run_dir / c.LEDGER_FILE).exists():
            c.die("no budget recorded and no ledger to estimate from; pass --budget")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ledger  # noqa: E402
        est = ledger.estimate_numbers(meta, ledger.load_ledger(run_dir), c.load_candidates(run_dir))
        meta["budget"] = est["total_invocations"]
    meta["approved"] = True
    c.fail_if(c.validate_part(meta, "metadata"))
    c.write_json(run_dir / c.METADATA_FILE, meta)
    c.emit({"approved": True, "budget": meta["budget"]})


def cmd_count(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    meta = c.load_metadata(run_dir)
    if args.n < 1:
        c.die("--n must be a positive integer; invocations only ever accumulate")
    meta["invocations"][args.role] += args.n
    total = sum(meta["invocations"].values())
    over = meta["budget"] is not None and total > meta["budget"]
    c.fail_if(c.validate_part(meta, "metadata"))
    c.write_json(run_dir / c.METADATA_FILE, meta)
    c.emit({"invocations": meta["invocations"], "total": total, "budget": meta["budget"], "over_budget": over})
    if over:
        print("WARNING: invocations exceed the recorded budget", file=sys.stderr)


def cmd_set_status(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir)
    meta = c.load_metadata(run_dir)
    if args.status == "incomplete" and not args.reason:
        c.die("incomplete needs --reason")
    if args.status == "complete" and (run_dir / c.LEDGER_FILE).exists():
        # A complete run has nothing left undecided; otherwise it is incomplete
        # with a reason, and the report says so.
        units = c.read_json(run_dir / c.LEDGER_FILE)
        cands = c.load_candidates(run_dir)
        open_units = [u["coverage_id"] for u in units if isinstance(u, dict) and u.get("status") in ("planned", "in_progress")]
        pending = [r["fingerprint"] for key in ("candidates", "carried") for r in cands[key]]
        if open_units or pending:
            c.die(f"the run is not complete: {len(open_units)} planned/in_progress unit(s), {len(pending)} undecided candidate(s); defer or decide them, or set incomplete with a reason")
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

    p = sub.add_parser("approve")
    p.add_argument("run_dir")
    p.add_argument("--budget", type=int)
    p.set_defaults(func=cmd_approve)

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
