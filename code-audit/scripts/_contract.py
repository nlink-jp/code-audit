#!/usr/bin/env python3
"""Shared contract helpers for the code-audit scripts (stdlib only).

Loaded by run.py, ledger.py, findings.py, compile.py and classes.py from the
same directory. Holds the schema-subset validator, JSON I/O, path rules,
identifier rules, coverage-id derivation and source digests, so that every
script applies exactly one definition of each.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"

AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
FINGERPRINT_RE = re.compile(r"^(?=.*[A-Za-z0-9])[A-Za-z0-9.][A-Za-z0-9._:/@+-]*$")  # a dot-file such as .gitignore may lead
CHECK_LOG_RE = re.compile(r"^checks/[a-z0-9][a-z0-9-]{0,63}\.log$")
WINDOWS_DEVICES = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}

IMPACT_ORDER = ["informational", "low", "medium", "high", "critical"]
CONFIDENCE_ORDER = ["low", "medium", "high"]

QUICK_SUBSYSTEM_REF = "profile/quick/all-in-scope-subsystems"

FINDINGS_FILE = "findings.json"
LEDGER_FILE = "coverage-ledger.json"
METADATA_FILE = "run-metadata.json"
COMMANDS_FILE = "commands.json"
CANDIDATES_FILE = "candidates.json"
NOTES_FILE = "notes.json"
REPLACEMENTS_FILE = "replacements.json"
CHECKS_DIR = "checks"


# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        die(f"{path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{path}: invalid JSON: {exc}")


def write_json(path: Path, data: object) -> None:
    """Atomic write: the file is either the old content or the new one."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def inert(text: str) -> str:
    """One line for the parent's terminal: no control or format character.
    Error messages quote offending values, and those values came from the
    target or a sub-agent."""
    return "".join(ch for ch in text if not unicodedata.category(ch).startswith("C"))


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {inert(message)}", file=sys.stderr)
    sys.exit(code)


def fail_if(errors: list[str]) -> None:
    if errors:
        for err in errors:
            print(f"ERROR: {inert(err)}", file=sys.stderr)
        sys.exit(1)


def emit(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Schema-subset validator
# ---------------------------------------------------------------------------

_SCHEMA: dict | None = None


def schema_part(name: str) -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    parts = _SCHEMA["parts"]
    if name not in parts:
        die(f"schema.json has no part '{name}'")
    return parts[name]


def check(value: object, schema: dict, path: str, errors: list[str]) -> None:
    """Validate value against the subset of JSON Schema used by schema.json:
    type (and type unions with null), const, enum, required, properties,
    additionalProperties:false, items, minItems, maxItems, minLength,
    pattern, minimum, maximum."""
    t = schema.get("type")
    types = t if isinstance(t, list) else [t]
    if value is None:
        if "null" not in types:
            errors.append(f"{path}: expected {t}, got null")
        return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}, got {value!r}")
        return
    if "object" in types:
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required field '{req}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                check(value[key], sub, f"{path}.{key}", errors)
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}: unexpected field '{key}'")
    elif "array" in types:
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: expected at least {min_items} item(s), got {len(value)}")
        max_items = schema.get("maxItems")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: expected at most {max_items} item(s), got {len(value)}")
        items = schema.get("items")
        if items:
            for i, v in enumerate(value):
                check(v, items, f"{path}[{i}]", errors)
    elif "string" in types:
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
            return
        enum = schema.get("enum")
        if enum and value not in enum:
            errors.append(f"{path}: '{value}' is not one of {enum}")
        min_len = schema.get("minLength")
        if min_len is not None and len(value.strip()) < min_len:
            errors.append(f"{path}: must have at least {min_len} visible character(s)")
        pattern = schema.get("pattern")
        if pattern:
            # An anchored pattern is matched whole: `$` alone would accept a
            # trailing newline and let one identifier exist twice.
            matched = re.fullmatch(pattern[1:-1], value) if pattern.startswith("^") and pattern.endswith("$") else re.search(pattern, value)
            if not matched:
                errors.append(f"{path}: '{value}' does not match pattern {pattern}")
    elif "boolean" in types:
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean, got {type(value).__name__}")
    elif "integer" in types:
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")
            return
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: {value} is below minimum {minimum}")
        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            errors.append(f"{path}: {value} is above maximum {maximum}")
    elif "number" in types:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path}: expected number, got {type(value).__name__}")


def validate_part(value: object, part: str, path: str = "$") -> list[str]:
    errors: list[str] = []
    check(value, schema_part(part), path, errors)
    return errors


# ---------------------------------------------------------------------------
# Paths and identifiers
# ---------------------------------------------------------------------------


def is_repo_relative(path: str) -> bool:
    """A repository-relative source path: not absolute, no traversal, no
    backslash, no empty or dot components."""
    if not path or path.startswith(("/", "~")) or "\\" in path or re.match(r"^[A-Za-z]:", path):
        return False
    parts = path.split("/")
    return all(p not in ("", ".", "..") for p in parts)


def is_agent_id(value: object) -> bool:
    return isinstance(value, str) and bool(AGENT_ID_RE.fullmatch(value)) and value not in WINDOWS_DEVICES


def is_fingerprint(value: object) -> bool:
    return isinstance(value, str) and bool(FINGERPRINT_RE.fullmatch(value))


def forbidden_char_errors(value: object, path: str) -> list[str]:
    """Strings anywhere in a sub-agent's return or a record may not carry
    control or format characters (terminal escapes, C1 controls,
    bidirectional overrides, zero-width characters): they would ride into
    the report and the terminal. Newline and tab are allowed, since code
    excerpts need them; the report makes them inert at its egress."""
    errors: list[str] = []
    if isinstance(value, str):
        for ch in value:
            if unicodedata.category(ch).startswith("C") and ch not in "\n\t":
                errors.append(f"{path}: control or format character U+{ord(ch):04X} is not allowed")
                break
    elif isinstance(value, dict):
        for k, v in value.items():
            errors += forbidden_char_errors(k, f"{path}.{k!r}" if forbidden_char_errors(k, "") else path)
            errors += forbidden_char_errors(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            errors += forbidden_char_errors(v, f"{path}[{i}]")
    return errors


def _identity(path: Path) -> tuple[int, int] | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def same_place(a: Path, b: Path) -> bool:
    """Compare two places by identity (device and inode), never by name: a
    case-insensitive or normalising disk gives one place many spellings."""
    ia, ib = _identity(a), _identity(b)
    return ia is not None and ia == ib


def is_inside(child: Path, parent: Path) -> bool:
    """Whether `child` is `parent` or lies beneath it, judged by identity.

    `child` need not exist yet: its nearest existing ancestor is taken, links
    are resolved there, and every ancestor is compared with `parent` by
    device and inode. A parent that does not exist contains nothing."""
    pid = _identity(parent)
    if pid is None:
        return False
    cur = Path(os.path.abspath(child))
    while not cur.exists():
        if cur.parent == cur:
            return False
        cur = cur.parent
    cur = Path(os.path.realpath(cur))
    while True:
        if _identity(cur) == pid:
            return True
        if cur.parent == cur:
            return False
        cur = cur.parent


# ---------------------------------------------------------------------------
# Coverage identity
# ---------------------------------------------------------------------------


def canonical_ref_error(ref: object) -> str | None:
    if not isinstance(ref, str) or not ref:
        return "empty"
    if unicodedata.normalize("NFC", ref) != ref:
        return "not NFC-normalized"
    if ref != ref.strip():
        return "surrounding whitespace"
    for ch in ref:
        cat = unicodedata.category(ch)
        if cat.startswith("C") or cat in ("Zl", "Zp"):
            return f"control or separator character U+{ord(ch):04X}"
    return None


def percent_encode(ref: str) -> str:
    return quote(ref, safe="-._~")


def coverage_id(refs: dict) -> str:
    parts = [percent_encode(refs[k]) for k in ("surface", "boundary", "subsystem", "attack_class")]
    if refs.get("lifecycle"):
        parts.append(percent_encode(refs["lifecycle"]))
    return "::".join(parts)


def semantic_tuple(refs: dict) -> tuple:
    return (refs["surface"], refs["boundary"], refs["subsystem"], refs["attack_class"], refs.get("lifecycle"))


# ---------------------------------------------------------------------------
# Source digests
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# Bounds for digesting a cited directory: the target is adversarial input and
# may plant a link to the whole disk or a huge tree under a cited path.
DIGEST_LIMITS = {"files": 50_000, "bytes": 256 * 1024 * 1024}
DIGEST_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}
DIGEST_SKIP_SUFFIXES = (".pyc", ".pyo")


def _regular_files(root: Path) -> Iterable[Path]:
    """Regular files under root, never through a link, skipping caches and
    VCS internals; yields in sorted order so the digest is stable."""
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in DIGEST_SKIP_DIRS and not (Path(dirpath) / d).is_symlink())
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if name.endswith(DIGEST_SKIP_SUFFIXES):
                continue
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            yield p


def lstat_no_links(target: Path, rel: str) -> os.stat_result | None:
    """lstat of target/rel where no component of rel may be a link: a link
    in the middle of the path would carry the walk outside the target. Returns
    the final component's lstat, a link's lstat when any component is a link
    (so the caller records 'symlink'), or None when something is missing."""
    cur = target
    for part in rel.split("/"):
        cur = cur / part
        try:
            st = os.lstat(cur)
        except OSError:
            return None
        if stat.S_ISLNK(st.st_mode):
            return st
    return st


def digests_for(target: Path, paths: Iterable[str]) -> dict[str, str]:
    """sha256 per repository-relative path. Values other than a digest:
    'missing' (no such regular file or directory), 'symlink' (the cited path
    is a link; links are never followed), 'invalid' (not repository-relative),
    'too-large' (a directory past DIGEST_LIMITS). Directories are digested as
    the sorted list of their regular files' digests so a unit may cite a
    package path; caches and VCS internals are skipped."""
    out: dict[str, str] = {}
    for rel in sorted(set(paths)):
        if not is_repo_relative(rel):
            out[rel] = "invalid"
            continue
        p = target / rel
        st = lstat_no_links(target, rel)
        if st is None:
            out[rel] = "missing"
            continue
        if stat.S_ISLNK(st.st_mode):
            out[rel] = "symlink"
        elif stat.S_ISREG(st.st_mode):
            out[rel] = "too-large" if st.st_size > DIGEST_LIMITS["bytes"] else sha256_file(p)
        elif stat.S_ISDIR(st.st_mode):
            h = hashlib.sha256()
            files = total = 0
            for f in _regular_files(p):
                files += 1
                total += f.stat().st_size
                if files > DIGEST_LIMITS["files"] or total > DIGEST_LIMITS["bytes"]:
                    out[rel] = "too-large"
                    break
                h.update(str(f.relative_to(target)).encode("utf-8"))
                h.update(sha256_file(f).encode("ascii"))
            else:
                out[rel] = h.hexdigest()
        else:
            out[rel] = "missing"
    return out


DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def is_digest(value: object) -> bool:
    return isinstance(value, str) and bool(DIGEST_RE.fullmatch(value))


def digests_unchanged(recorded: dict, current: dict) -> bool:
    """Unchanged only when every recorded value is a real digest and the
    current one equals it. 'missing', 'symlink' or 'too-large' twice is not
    evidence that anything stayed the same."""
    if not recorded:
        return False
    return all(is_digest(v) and current.get(k) == v for k, v in recorded.items())


# ---------------------------------------------------------------------------
# Run directory
# ---------------------------------------------------------------------------


def run_file(run_dir: Path, name: str) -> Path:
    return run_dir / name


def load_metadata(run_dir: Path) -> dict:
    data = read_json(run_file(run_dir, METADATA_FILE))
    fail_if(validate_part(data, "metadata"))
    return data  # type: ignore[return-value]


CANDIDATE_KEYS = ("candidates", "carried", "decided", "suppressed", "uncovered", "resolved_prior_leads", "unlinked_prior", "changed_prior", "agents_seen")


def load_candidates(run_dir: Path) -> dict:
    path = run_file(run_dir, CANDIDATES_FILE)
    data = read_json(path) if path.exists() else {}
    if not isinstance(data, dict):
        die(f"{path}: expected an object")
    for key in CANDIDATE_KEYS:
        data.setdefault(key, [])
    return data


def save_candidates(run_dir: Path, data: dict) -> None:
    write_json(run_file(run_dir, CANDIDATES_FILE), data)


def load_findings(run_dir: Path) -> list:
    path = run_file(run_dir, FINDINGS_FILE)
    if not path.exists():
        return []
    data = read_json(path)
    if not isinstance(data, list):
        die(f"{path}: expected a top-level array")
    return data


def load_notes(run_dir: Path) -> list:
    path = run_file(run_dir, NOTES_FILE)
    if not path.exists():
        return []
    data = read_json(path)
    if not isinstance(data, list):
        die(f"{path}: expected a top-level array")
    return data


def save_notes(run_dir: Path, notes: list) -> None:
    write_json(run_file(run_dir, NOTES_FILE), notes)


def load_replacements(run_dir: Path) -> list:
    path = run_file(run_dir, REPLACEMENTS_FILE)
    if not path.exists():
        return []
    data = read_json(path)
    if not isinstance(data, list):
        die(f"{REPLACEMENTS_FILE}: must be an array")
    return data


def save_replacements(run_dir: Path, items: list) -> None:
    write_json(run_file(run_dir, REPLACEMENTS_FILE), items)
