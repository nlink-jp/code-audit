#!/usr/bin/env python3
"""Hunting-class files of the code-audit skill (stdlib only).

Usage:
    classes.py list  [--classes <dir>]
    classes.py size  [--classes <dir>] [--max-bytes N]
    classes.py check-knowledge --knowledge <dir> [--adr <dir>] [--origin <dir>] [--classes <dir>]

A class file is Markdown. Each class is a level-2 heading followed, before
any other content, by one `Source:` line naming where the lesson is
recorded: `security.md#Heading text` (a document under the knowledge
repository's docs/en/), `ADR-021` (an organization ADR), or
`origin:ATTACK-CLASSES.md#Injection` (a block of the skill this design
derives from, cloudflare/security-audit-skill at commit c1c8a8c, under
skills/security-audit/; its class blocks are bold names, which count as
headings). Several sources are separated by commas; a comma inside a heading
is kept, since the split happens only before the next `ADR-NNN`, `doc.md#`
or `origin:`. `check-knowledge` verifies that every cited knowledge heading
exists; ADR and origin references are checked when --adr / --origin name the
directories and reported as unchecked otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _contract as c  # noqa: E402

DEFAULT_CLASSES = Path(__file__).resolve().parent.parent / "classes"
HEADING_RE = re.compile(r"^## +(.+?)\s*$")
SOURCE_RE = re.compile(r"^Source:\s*(.+?)\s*$")
ADR_RE = re.compile(r"^ADR-(\d{3})$")
KNOWLEDGE_RE = re.compile(r"^([A-Za-z0-9_.-]+\.md)#(.+)$")
ORIGIN_RE = re.compile(r"^origin:([A-Za-z0-9_.-]+\.md)#(.+)$")
ORIGIN_SUBDIR = Path("skills") / "security-audit"
# A comma separates two references only when another reference starts after
# it; headings themselves may contain commas.
SPLIT_RE = re.compile(r",\s*(?=ADR-\d{3}\b|origin:[A-Za-z0-9_.-]+\.md#|[A-Za-z0-9_.-]+\.md#)")


def parse_class_file(path: Path) -> tuple[list[dict], list[str]]:
    classes: list[dict] = []
    errors: list[str] = []
    current: dict | None = None
    awaiting_source = False
    in_fence = False
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            if current and awaiting_source:
                errors.append(f"{path.name}:{current['line']}: class '{current['name']}' has no Source: line")
            current = {"file": path.name, "name": m.group(1), "line": lineno, "sources": []}
            classes.append(current)
            awaiting_source = True
            continue
        if current is None:
            continue
        s = SOURCE_RE.match(line)
        if s:
            if not awaiting_source:
                errors.append(f"{path.name}:{lineno}: Source: must directly follow the class heading")
            for ref in (x.strip() for x in SPLIT_RE.split(s.group(1))):
                if ADR_RE.match(ref):
                    current["sources"].append({"kind": "adr", "ref": ref})
                elif ORIGIN_RE.match(ref):
                    doc, heading = ORIGIN_RE.match(ref).groups()  # type: ignore[union-attr]
                    current["sources"].append({"kind": "origin", "doc": doc, "heading": heading, "ref": ref})
                elif KNOWLEDGE_RE.match(ref):
                    doc, heading = KNOWLEDGE_RE.match(ref).groups()  # type: ignore[union-attr]
                    current["sources"].append({"kind": "knowledge", "doc": doc, "heading": heading, "ref": ref})
                else:
                    errors.append(f"{path.name}:{lineno}: unrecognised source '{ref}' (want doc.md#Heading, ADR-NNN or origin:FILE.md#Heading)")
            awaiting_source = False
            continue
        if line.strip() and awaiting_source:
            errors.append(f"{path.name}:{lineno}: class '{current['name']}' needs a Source: line before its body")
            awaiting_source = False
    if current and awaiting_source:
        errors.append(f"{path.name}:{current['line']}: class '{current['name']}' has no Source: line")
    return classes, errors


def load_classes(classes_dir: Path) -> tuple[list[dict], list[str]]:
    if not classes_dir.is_dir():
        return [], [f"{classes_dir}: not a directory"]
    all_classes: list[dict] = []
    errors: list[str] = []
    for path in sorted(classes_dir.glob("*.md")):
        cl, errs = parse_class_file(path)
        all_classes += cl
        errors += errs
    seen: dict[str, str] = {}
    for cl in all_classes:
        key = f"{cl['file']}#{cl['name']}"
        if key in seen:
            errors.append(f"{cl['file']}:{cl['line']}: duplicate class name '{cl['name']}'")
        seen[key] = cl["file"]
    return all_classes, errors


def headings_in(path: Path, bold_blocks: bool = False) -> set[str]:
    """Markdown headings of a document; with bold_blocks, a line that starts
    with a bold name (`**Injection** ...`) counts too — the origin skill names
    its attack classes that way."""
    out: set[str] = set()
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^#{1,6} +(.+?)\s*$", line)
        if m:
            out.add(m.group(1))
        elif bold_blocks:
            b = re.match(r"^\*\*(.+?)\*\*", line)
            if b:
                out.add(b.group(1))
    return out


def cmd_list(args: argparse.Namespace) -> None:
    classes, errors = load_classes(Path(args.classes))
    c.fail_if(errors)
    c.emit([{"file": cl["file"], "name": cl["name"], "sources": [s["ref"] for s in cl["sources"]]} for cl in classes])


def cmd_size(args: argparse.Namespace) -> None:
    classes_dir = Path(args.classes)
    _, errors = load_classes(classes_dir)
    sizes = {p.name: p.stat().st_size for p in sorted(classes_dir.glob("*.md"))} if classes_dir.is_dir() else {}
    for name, size in sizes.items():
        if size > args.max_bytes:
            errors.append(f"{name}: {size} bytes exceeds {args.max_bytes}")
    c.fail_if(errors)
    c.emit({"max_bytes": args.max_bytes, "files": sizes})


def cmd_check_knowledge(args: argparse.Namespace) -> None:
    classes, errors = load_classes(Path(args.classes))
    knowledge = Path(args.knowledge)
    docs = knowledge / "docs" / "en"
    if not docs.is_dir():
        c.die(f"{docs}: not a directory; --knowledge must be the knowledge repository root")
    adr_dir = Path(args.adr) if args.adr else None
    origin_dir = Path(args.origin) / ORIGIN_SUBDIR if args.origin else None
    if origin_dir is not None and not origin_dir.is_dir():
        c.die(f"{origin_dir}: not a directory; --origin must be a checkout of cloudflare/security-audit-skill")
    heading_cache: dict[str, set[str]] = {}
    checked = unchecked = origin_unchecked = 0
    for cl in classes:
        if not cl["sources"]:
            errors.append(f"{cl['file']}:{cl['line']}: class '{cl['name']}' cites no source")
        for s in cl["sources"]:
            if s["kind"] == "origin":
                if origin_dir is None:
                    origin_unchecked += 1
                    continue
                doc = origin_dir / s["doc"]
                if not doc.is_file():
                    errors.append(f"{cl['file']}:{cl['line']}: {s['ref']}: no such document in the origin")
                    continue
                key = f"origin:{s['doc']}"
                if key not in heading_cache:
                    heading_cache[key] = headings_in(doc, bold_blocks=True)
                if s["heading"] not in heading_cache[key]:
                    errors.append(f"{cl['file']}:{cl['line']}: {s['ref']}: heading or block not found in the origin's {s['doc']}")
                checked += 1
            elif s["kind"] == "knowledge":
                doc = docs / s["doc"]
                if not doc.is_file():
                    errors.append(f"{cl['file']}:{cl['line']}: {s['ref']}: no such document under docs/en")
                    continue
                if s["doc"] not in heading_cache:
                    heading_cache[s["doc"]] = headings_in(doc)
                if s["heading"] not in heading_cache[s["doc"]]:
                    errors.append(f"{cl['file']}:{cl['line']}: {s['ref']}: heading not found in {s['doc']}")
                checked += 1
            else:
                if adr_dir is None:
                    unchecked += 1
                    continue
                num = ADR_RE.match(s["ref"]).group(1)  # type: ignore[union-attr]
                if not any(adr_dir.glob(f"{num}-*.md")):
                    errors.append(f"{cl['file']}:{cl['line']}: {s['ref']}: no ADR file {num}-*.md in {adr_dir}")
                checked += 1
    c.fail_if(errors)
    c.emit({"classes": len(classes), "sources_checked": checked, "adr_unchecked": unchecked, "origin_unchecked": origin_unchecked})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list")
    p.add_argument("--classes", default=str(DEFAULT_CLASSES))
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("size")
    p.add_argument("--classes", default=str(DEFAULT_CLASSES))
    p.add_argument("--max-bytes", type=int, default=16384)
    p.set_defaults(func=cmd_size)

    p = sub.add_parser("check-knowledge")
    p.add_argument("--knowledge", required=True)
    p.add_argument("--adr")
    p.add_argument("--origin")
    p.add_argument("--classes", default=str(DEFAULT_CLASSES))
    p.set_defaults(func=cmd_check_knowledge)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
