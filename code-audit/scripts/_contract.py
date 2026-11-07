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
import sys
import unicodedata
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.json"

AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
FINGERPRINT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")
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


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def fail_if(errors: list[str]) -> None:
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
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
        if pattern and not re.search(pattern, value):
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
    return isinstance(value, str) and bool(AGENT_ID_RE.match(value)) and value not in WINDOWS_DEVICES


def is_fingerprint(value: object) -> bool:
    return isinstance(value, str) and bool(FINGERPRINT_RE.match(value))


def same_place(a: Path, b: Path) -> bool:
    """Compare two places by identity (resolved path), never by name."""
    return a.resolve() == b.resolve()


def is_inside(child: Path, parent: Path) -> bool:
    c, p = child.resolve(), parent.resolve()
    return c == p or p in c.parents


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


def digests_for(target: Path, paths: Iterable[str]) -> dict[str, str]:
    """sha256 per repository-relative path; 'missing' when the path is not a
    regular file. Directories are digested as the sorted list of their
    regular files' digests so a unit may cite a package path."""
    out: dict[str, str] = {}
    for rel in sorted(set(paths)):
        p = target / rel
        if p.is_file():
            out[rel] = sha256_file(p)
        elif p.is_dir():
            h = hashlib.sha256()
            for f in sorted(x for x in p.rglob("*") if x.is_file() and ".git" not in x.parts):
                h.update(str(f.relative_to(target)).encode("utf-8"))
                h.update(sha256_file(f).encode("ascii"))
            out[rel] = h.hexdigest()
        else:
            out[rel] = "missing"
    return out


def digests_unchanged(recorded: dict, current: dict) -> bool:
    if not recorded:
        return False
    return all(current.get(k) == v for k, v in recorded.items())


# ---------------------------------------------------------------------------
# Run directory
# ---------------------------------------------------------------------------


def run_file(run_dir: Path, name: str) -> Path:
    return run_dir / name


def load_metadata(run_dir: Path) -> dict:
    data = read_json(run_file(run_dir, METADATA_FILE))
    fail_if(validate_part(data, "metadata"))
    return data  # type: ignore[return-value]


def load_candidates(run_dir: Path) -> dict:
    path = run_file(run_dir, CANDIDATES_FILE)
    if not path.exists():
        return {"candidates": [], "carried": [], "decided": [], "suppressed": [], "uncovered": [], "resolved_prior_leads": []}
    return read_json(path)  # type: ignore[return-value]


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
