#!/usr/bin/env python3
"""Behaviour tests for the bundled scripts (stdlib only).

Runs run.py, ledger.py, findings.py, compile.py and classes.py as
subprocesses — the same way the skill invokes them — against the fixture
sample repository, unit proposals, hunter and critic results and records, and
pins repository-wide invariants:

- every bundled script imports only the standard library (and its siblings);
- no file inside the distribution boundary carries an absolute local path;
- coverage_id is derived in exactly one place;
- SKILL.md never instructs writing a ledger or findings file directly;
- compile.py keeps code inside fences.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "code-audit"
SCRIPTS = SKILL / "scripts"
FIXTURES = REPO / "tests" / "fixtures"
SAMPLE_REPO = FIXTURES / "sample-repo"

STDLIB = set(getattr(sys, "stdlib_module_names", ()))  # Python 3.10+; empty on 3.9
ABSOLUTE_PATH = re.compile(r"(?<![\w/])/(?:Users|home|private|Volumes)/")
OWNED_FILES = ("coverage-ledger.json", "findings.json", "candidates.json", "run-metadata.json", "notes.json")
OWNING_SCRIPTS = ("ledger.py", "findings.py", "run.py")


def run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args], capture_output=True, text=True, cwd=str(cwd) if cwd else None)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def script_files() -> list[Path]:
    return sorted(SCRIPTS.glob("*.py")) if SCRIPTS.is_dir() else []


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


# ---------------------------------------------------------------------------
# Invariants of the distribution boundary
# ---------------------------------------------------------------------------


class DistributionBoundaryTests(unittest.TestCase):
    def test_bundled_scripts_import_only_stdlib(self) -> None:
        if not STDLIB:
            self.skipTest("sys.stdlib_module_names needs Python 3.10+")
        siblings = {p.stem for p in script_files()}
        for script in script_files():
            with self.subTest(script=script.name):
                extra = imported_modules(script) - STDLIB - siblings
                self.assertEqual(extra, set(), f"{script.name} imports non-stdlib modules")

    def test_no_absolute_local_paths_in_skill_content(self) -> None:
        for path in sorted(SKILL.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            with self.subTest(file=str(path.relative_to(REPO))):
                self.assertIsNone(ABSOLUTE_PATH.search(text), "absolute local path in skill content")

    def test_frontmatter_name_is_the_slash_command(self) -> None:
        head = (SKILL / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        self.assertIn("name: code-audit", head)

    def test_coverage_id_is_derived_in_one_place(self) -> None:
        definitions = [p.name for p in script_files() if re.search(r"^def coverage_id\(", p.read_text(encoding="utf-8"), re.M)]
        self.assertEqual(definitions, ["_contract.py"])
        callers = {p.name for p in script_files() if re.search(r"\bcoverage_id\(", p.read_text(encoding="utf-8"))}
        self.assertTrue(callers <= {"_contract.py", "ledger.py"}, callers)

    def test_skill_md_never_instructs_direct_writes_of_owned_files(self) -> None:
        for lineno, line in enumerate((SKILL / "SKILL.md").read_text(encoding="utf-8").splitlines(), start=1):
            if any(f in line for f in OWNED_FILES):
                with self.subTest(line=lineno):
                    self.assertTrue(any(s in line for s in OWNING_SCRIPTS), f"SKILL.md:{lineno} names an owned file without its owning script: {line.strip()}")


# ---------------------------------------------------------------------------
# A full run over the fixture repository
# ---------------------------------------------------------------------------


class RunFixture(unittest.TestCase):
    """Shared helpers: a fresh target copy and an initialised run directory."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmpdir = Path(self.tmp.name)
        self.target = self.tmpdir / "target"
        shutil.copytree(SAMPLE_REPO, self.target)
        self.d1 = sha256(self.target / "app" / "files.py")
        self.d2 = sha256(self.target / "tests" / "test_files.py")
        self.run_dir = self.tmpdir / "out" / "run-1"
        self.ok(run("run.py", "init", "--target", str(self.target), "--output", str(self.run_dir)))
        shutil.copy(FIXTURES / "commands.json", self.run_dir / "commands.json")

    def ok(self, proc: subprocess.CompletedProcess) -> dict | list:
        self.assertEqual(proc.returncode, 0, f"stdout={proc.stdout}\nstderr={proc.stderr}")
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def refused(self, proc: subprocess.CompletedProcess, needle: str) -> None:
        self.assertNotEqual(proc.returncode, 0, f"expected refusal, got stdout={proc.stdout}")
        self.assertIn(needle, proc.stderr)

    def ledger(self) -> list:
        return json.loads((self.run_dir / "coverage-ledger.json").read_text(encoding="utf-8"))

    def unit_ids(self) -> tuple[str, str]:
        units = self.ledger()
        u1 = next(u["coverage_id"] for u in units if u["attack_class"] == "Resource and file handling")
        u2 = next(u["coverage_id"] for u in units if u["attack_class"] == "Injection")
        return u1, u2

    def fill(self, name: str) -> Path:
        text = (FIXTURES / name).read_text(encoding="utf-8")
        if (self.run_dir / "coverage-ledger.json").exists():
            u1, u2 = self.unit_ids()
            text = text.replace("__U1__", u1).replace("__U2__", u2)
        text = text.replace("__D1__", self.d1).replace("__D2__", self.d2)
        out = self.tmpdir / name
        out.write_text(text, encoding="utf-8")
        return out

    def write_json(self, data: object, name: str) -> Path:
        path = self.tmpdir / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def seed(self, *extra: str) -> dict:
        return self.ok(run("ledger.py", "seed", str(self.run_dir), "--target", str(self.target), "--units", str(FIXTURES / "units.json"), *extra))

    def hunt(self) -> dict:
        """seed → exec unit-tests → assign → record. Returns the record summary."""
        self.seed()
        self.ok(run("run.py", "exec", str(self.run_dir), "unit-tests", "--target", str(self.target)))
        u1, u2 = self.unit_ids()
        self.ok(run("ledger.py", "assign", str(self.run_dir), "--agent", "hunter-1", u1, u2))
        return self.ok(run("ledger.py", "record", str(self.run_dir), str(self.fill("hunter-result.json"))))

    def hunter_result(self) -> dict:
        return json.loads(self.fill("hunter-result.json").read_text(encoding="utf-8"))

    def candidate_record(self, index: int, **overrides: object) -> dict:
        cand = dict(self.hunter_result()["candidates"][index])
        rec = {"verdict": cand.pop("proposed_verdict"), **cand}
        rec.update(overrides)
        return rec


class RunPyTests(RunFixture):
    def test_init_writes_metadata_without_absolute_paths(self) -> None:
        meta = json.loads((self.run_dir / "run-metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["run_id"], "run-1")
        self.assertEqual(meta["repo"], "target")
        self.assertEqual(meta["source_ref"], "unversioned")
        self.assertTrue(meta["dirty"])
        self.assertEqual(meta["execution_policy"], "read-and-existing-tests")
        self.assertNotIn(str(self.tmpdir), (self.run_dir / "run-metadata.json").read_text(encoding="utf-8"))
        self.assertTrue((self.run_dir / "checks").is_dir())
        self.ok(run("run.py", "validate", str(self.run_dir)))

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_init_takes_repo_name_from_git_remote(self) -> None:
        target = self.tmpdir / "gitrepo"
        shutil.copytree(SAMPLE_REPO, target)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        for cmd in (["git", "init", "-q"], ["git", "add", "."], ["git", "commit", "-q", "-m", "fixture"], ["git", "remote", "add", "origin", "https://github.com/example/sample.git"]):
            subprocess.run(cmd, cwd=str(target), check=True, capture_output=True, env=env)
        out = self.ok(run("run.py", "init", "--target", str(target), "--output", str(self.tmpdir / "out2")))
        self.assertEqual(out["repo"], "example/sample")
        self.assertFalse(out["dirty"])
        self.assertRegex(out["source_ref"], r"^[0-9a-f]{40}$")

    def test_init_refuses_output_inside_target(self) -> None:
        self.refused(run("run.py", "init", "--target", str(self.target), "--output", str(self.target / "audit")), "inside the target")
        self.refused(run("run.py", "init", "--target", str(self.target), "--output", str(self.target)), "inside the target")
        self.refused(run("run.py", "init", "--target", str(self.target), "--output", str(self.tmpdir)), "target is inside the output")

    def test_init_refuses_non_empty_output(self) -> None:
        self.refused(run("run.py", "init", "--target", str(self.target), "--output", str(self.run_dir)), "not empty")

    def test_init_records_prior_runs_by_name(self) -> None:
        out = self.ok(run("run.py", "init", "--target", str(self.target), "--output", str(self.tmpdir / "out" / "run-2"), "--prior", str(self.run_dir)))
        meta = json.loads((self.tmpdir / "out" / "run-2" / "run-metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["prior_runs"], ["run-1"])
        self.assertEqual(out["run_id"], "run-2")
        self.refused(run("run.py", "init", "--target", str(self.target), "--output", str(self.tmpdir / "out" / "run-3"), "--prior", str(self.tmpdir)), "prior run has no")

    def test_budget_count_and_status(self) -> None:
        self.ok(run("run.py", "set-budget", str(self.run_dir), "3"))
        self.ok(run("run.py", "count", str(self.run_dir), "reconnaissance", "--n", "4"))
        out = self.ok(run("run.py", "count", str(self.run_dir), "hunter"))
        self.assertEqual(out["total"], 5)
        self.assertTrue(out["over_budget"])
        self.refused(run("run.py", "set-status", str(self.run_dir), "incomplete"), "needs --reason")
        out = self.ok(run("run.py", "set-status", str(self.run_dir), "incomplete", "--reason", "validation_budget_exhausted"))
        self.assertEqual(out["incomplete_reason"], "validation_budget_exhausted")
        out = self.ok(run("run.py", "set-status", str(self.run_dir), "complete"))
        self.assertIsNone(out["incomplete_reason"])

    def test_exec_runs_only_allowed_ledger_commands(self) -> None:
        out = self.ok(run("run.py", "exec", str(self.run_dir), "unit-tests", "--target", str(self.target)))
        self.assertEqual(out["exit_code"], 0)
        log = (self.run_dir / "checks" / "unit-tests.log").read_text(encoding="utf-8")
        self.assertIn("command_id: unit-tests", log)
        self.assertIn("exit_code: 0", log)
        self.assertIn("Ran 1 test", log)
        self.refused(run("run.py", "exec", str(self.run_dir), "fetch-deps", "--target", str(self.target)), "forbidden")
        self.refused(run("run.py", "exec", str(self.run_dir), "not-in-ledger", "--target", str(self.target)), "only ledger commands run")
        self.assertFalse((self.run_dir / "checks" / "fetch-deps.log").exists())

    def test_exec_starts_from_an_empty_environment(self) -> None:
        env = {**os.environ, "CODE_AUDIT_TEST_SECRET": "leak-me", "ANOTHER_TOKEN": "x"}
        proc = subprocess.run([sys.executable, str(SCRIPTS / "run.py"), "exec", str(self.run_dir), "env-probe", "--target", str(self.target)], capture_output=True, text=True, env=env)
        out = self.ok(proc)
        self.assertEqual(out["exit_code"], 0)
        log = (self.run_dir / "checks" / "env-probe.log").read_text(encoding="utf-8")
        names = set(json.loads(log.split("--- stdout ---\n", 1)[1].split("\n--- stderr ---", 1)[0].strip()))
        self.assertIn("PATH", names)
        self.assertIn("HOME", names)
        self.assertNotIn("CODE_AUDIT_TEST_SECRET", names)
        self.assertNotIn("ANOTHER_TOKEN", names)
        self.assertNotIn("leak-me", log)

    def test_exec_enforces_the_time_limit_on_the_whole_process_group(self) -> None:
        out = self.ok(run("run.py", "exec", str(self.run_dir), "slow", "--target", str(self.target)))
        self.assertTrue(out["timed_out"])
        self.assertIsNone(out["exit_code"])
        # the fixture's grandchild sleeps 30 s; killing only the child would
        # leave it holding the pipes and exec would wait for it
        self.assertLess(out["duration_sec"], 10)

    @unittest.skipUnless(shutil.which("git"), "git not available")
    def test_init_does_not_run_commands_named_in_the_target_git_config(self) -> None:
        target = self.tmpdir / "hostile"
        shutil.copytree(SAMPLE_REPO, target)
        marker = self.tmpdir / "fsmonitor-ran"
        hook = self.tmpdir / "fsmonitor.sh"
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nprintf '/'\n", encoding="utf-8")
        hook.chmod(0o755)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        for cmd in (["git", "init", "-q"], ["git", "add", "."], ["git", "commit", "-q", "-m", "fixture"], ["git", "config", "core.fsmonitor", str(hook)]):
            subprocess.run(cmd, cwd=str(target), check=True, capture_output=True, env=env)
        out = self.ok(run("run.py", "init", "--target", str(target), "--output", str(self.tmpdir / "out-hostile")))
        self.assertRegex(out["source_ref"], r"^[0-9a-f]{40}$")
        self.assertFalse(marker.exists(), "the target's core.fsmonitor command ran during init")

    def test_validate_rejects_forbidden_command_without_reason(self) -> None:
        data = json.loads((FIXTURES / "commands.json").read_text(encoding="utf-8"))
        data["commands"][1]["reason"] = ""
        (self.run_dir / "commands.json").write_text(json.dumps(data), encoding="utf-8")
        self.refused(run("run.py", "validate", str(self.run_dir)), "needs a reason")


class LedgerTests(RunFixture):
    def test_seed_derives_ids_and_digests(self) -> None:
        out = self.seed()
        self.assertEqual(out["units"], 2)
        units = self.ledger()
        self.assertEqual([u["status"] for u in units], ["planned", "planned"])
        self.assertEqual([u["prior_status"] for u in units], ["none", "none"])
        u1, _ = self.unit_ids()
        self.assertEqual(u1, "app%2Ffiles.py%23read_user_file::app%2Ffiles.py%23base_dir::app::classes%2Fgeneric.md%23Resource%20and%20file%20handling")
        unit = next(u for u in units if u["coverage_id"] == u1)
        self.assertEqual(unit["source_digests"], {"app/files.py": self.d1})
        self.assertEqual(units, sorted(units, key=lambda u: u["coverage_id"]))
        self.ok(run("ledger.py", "validate", str(self.run_dir)))
        self.refused(run("ledger.py", "seed", str(self.run_dir), "--target", str(self.target), "--units", str(FIXTURES / "units.json")), "seed runs once")

    def test_seed_refuses_duplicate_and_colliding_proposals(self) -> None:
        props = json.loads((FIXTURES / "units.json").read_text(encoding="utf-8"))
        dup = self.write_json([props[0], props[0]], "dup.json")
        self.refused(run("ledger.py", "seed", str(self.run_dir), "--target", str(self.target), "--units", str(dup)), "duplicate unit")
        bad = dict(props[0])
        bad["canonical_refs"] = {**props[0]["canonical_refs"], "surface": " padded"}
        self.refused(run("ledger.py", "seed", str(self.run_dir), "--target", str(self.target), "--units", str(self.write_json([bad], "bad.json"))), "surrounding whitespace")

    def test_quick_profile_collapses_the_subsystem(self) -> None:
        quick = self.tmpdir / "out" / "quick"
        self.ok(run("run.py", "init", "--target", str(self.target), "--output", str(quick), "--profile", "quick"))
        self.ok(run("ledger.py", "seed", str(quick), "--target", str(self.target), "--units", str(FIXTURES / "units.json")))
        units = json.loads((quick / "coverage-ledger.json").read_text(encoding="utf-8"))
        self.assertTrue(all(u["canonical_refs"]["subsystem"] == "profile/quick/all-in-scope-subsystems" for u in units))
        self.assertTrue(all("profile%2Fquick" in u["coverage_id"] for u in units))

    def test_assign_moves_planned_units_to_in_progress(self) -> None:
        self.seed()
        u1, u2 = self.unit_ids()
        self.refused(run("ledger.py", "assign", str(self.run_dir), "--agent", "Hunter", u1), "canonical agent id")
        self.refused(run("ledger.py", "assign", str(self.run_dir), "--agent", "con", u1), "canonical agent id")
        self.ok(run("ledger.py", "assign", str(self.run_dir), "--agent", "hunter-1", u1))
        unit = next(u for u in self.ledger() if u["coverage_id"] == u1)
        self.assertEqual((unit["status"], unit["agent_id"]), ("in_progress", "hunter-1"))
        self.refused(run("ledger.py", "assign", str(self.run_dir), "--agent", "hunter-2", u1), "only planned units")

    def test_record_applies_the_hunter_result(self) -> None:
        out = self.hunt()
        u1, u2 = self.unit_ids()
        self.assertEqual(out["units"], {u1: "candidate", u2: "covered"})
        self.assertEqual(len(out["queued_candidates"]), 3)
        units = {u["coverage_id"]: u for u in self.ledger()}
        self.assertEqual(units[u1]["result_fingerprints"], ["app/files.py:read_user_file:path-traversal", "app/files.py:read_user_file:symlink-escape", "app/files.py:list_user_files:enumeration"])
        self.assertEqual(units[u2]["checks"][0]["check_log"], "checks/unit-tests.log")
        self.assertEqual(units[u2]["reviewed_paths"], ["app/files.py", "tests/test_files.py"])
        cands = json.loads((self.run_dir / "candidates.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cands["candidates"]), 3)
        self.assertEqual(len(cands["uncovered"]), 1)
        notes = json.loads((self.run_dir / "notes.json").read_text(encoding="utf-8"))
        self.assertEqual([n["kind"] for n in notes], ["hardening", "out_of_scope"])
        self.assertTrue(all(n["agent_id"] == "hunter-1" for n in notes))
        status = self.ok(run("ledger.py", "status", str(self.run_dir)))
        self.assertEqual(status["counts"], {"candidate": 1, "covered": 1})

    def test_record_refuses_a_foreign_or_partial_result(self) -> None:
        self.seed()
        self.ok(run("run.py", "exec", str(self.run_dir), "unit-tests", "--target", str(self.target)))
        u1, u2 = self.unit_ids()
        self.ok(run("ledger.py", "assign", str(self.run_dir), "--agent", "hunter-1", u1, u2))
        result = self.hunter_result()
        other = dict(result, agent_id="hunter-9")
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(other, "other.json"))), "not in_progress under hunter-9")
        partial = dict(result, units=result["units"][:1])
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(partial, "partial.json"))), "appears exactly once")
        unclaimed = json.loads(json.dumps(result))
        unclaimed["units"][0]["candidate_fingerprints"] = unclaimed["units"][0]["candidate_fingerprints"][:1]
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(unclaimed, "unclaimed.json"))), "not listed in any reported unit")
        self.assertEqual([u["status"] for u in self.ledger()], ["in_progress", "in_progress"])

    def test_record_holds_candidates_to_the_findings_bar(self) -> None:
        self.seed()
        self.ok(run("run.py", "exec", str(self.run_dir), "unit-tests", "--target", str(self.target)))
        u1, u2 = self.unit_ids()
        self.ok(run("ledger.py", "assign", str(self.run_dir), "--agent", "hunter-1", u1, u2))
        result = self.hunter_result()
        result["candidates"][0]["confidence"]["score"] = "high"
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(result, "conf.json"))), "caps confidence at medium")
        result = self.hunter_result()
        result["candidates"][0]["severity"]["overall"] = "critical"
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(result, "sev.json"))), "cannot exceed demonstrated impact")
        result = self.hunter_result()
        result["candidates"][0]["evidence_kind"] = "existing_test"
        result["candidates"][0]["check_log"] = "checks/missing.log"
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(result, "log.json"))), "does not exist in the run directory")
        result = self.hunter_result()
        result["candidates"][0]["trace"][0]["kind"] = "sink"
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(result, "trace.json"))), "starts at entrypoint")
        result = self.hunter_result()
        result["candidates"][1]["validation_plan"] = {"local": "", "deployment": ""}
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(result, "plan.json"))), "non-empty local or deployment plan")
        result = self.hunter_result()
        result["candidates"][0]["evidence"][0]["file"] = "../outside.py"
        self.refused(run("ledger.py", "record", str(self.run_dir), str(self.write_json(result, "path.json"))), "repository-relative")

    def test_merge_critic_standard_adds_and_reassigns(self) -> None:
        self.hunt()
        u1, u2 = self.unit_ids()
        out = self.ok(run("ledger.py", "merge-critic", str(self.run_dir), str(self.fill("critic-result.json")), "--target", str(self.target)))
        self.assertEqual(len(out["added"]), 1)
        self.assertEqual(out["added_as"], "planned")
        self.assertEqual(out["reassigned"], [u2])
        self.assertTrue(out["work_remaining"])
        units = {u["coverage_id"]: u for u in self.ledger()}
        self.assertEqual(len(units), 3)
        self.assertEqual((units[u2]["status"], units[u2]["wave"], units[u2]["agent_id"]), ("planned", 2, None))
        self.assertEqual(units[u2]["attempts"][0]["agent_id"], "hunter-1")
        self.assertEqual(units[u2]["attempts"][0]["status"], "covered")
        self.refused(run("ledger.py", "assign", str(self.run_dir), "--agent", "hunter-1", u2), "fresh owner")
        self.ok(run("ledger.py", "assign", str(self.run_dir), "--agent", "hunter-2", u2))
        self.ok(run("ledger.py", "validate", str(self.run_dir)))

    def test_merge_critic_quick_defers_instead(self) -> None:
        quick = self.tmpdir / "out" / "quick"
        self.ok(run("run.py", "init", "--target", str(self.target), "--output", str(quick), "--profile", "quick"))
        self.ok(run("ledger.py", "seed", str(quick), "--target", str(self.target), "--units", str(FIXTURES / "units.json")))
        units = json.loads((quick / "coverage-ledger.json").read_text(encoding="utf-8"))
        u2 = next(u["coverage_id"] for u in units if u["attack_class"] == "Injection")
        critic = json.loads((FIXTURES / "critic-result.json").read_text(encoding="utf-8"))
        critic["reassign_ids"] = []
        out = self.ok(run("ledger.py", "merge-critic", str(quick), str(self.write_json(critic, "critic-quick.json")), "--target", str(self.target)))
        self.assertEqual(out["added_as"], "deferred")
        self.assertFalse(out["work_remaining"])
        added = next(u for u in json.loads((quick / "coverage-ledger.json").read_text(encoding="utf-8")) if u["coverage_id"] == out["added"][0])
        self.assertEqual(added["status"], "deferred")
        self.assertTrue(added["unresolved"][0].startswith("quick_profile_final_critic"))
        self.assertIn(u2, [u["coverage_id"] for u in units])

    def test_defer_and_estimate(self) -> None:
        self.seed()
        est = self.ok(run("ledger.py", "estimate", str(self.run_dir), "--tokens-per-invocation", "50000"))
        self.assertEqual((est["hunters"], est["critics"], est["verification_stages"]), (2, 3, 2))
        self.assertEqual(est["tokens_estimate"], est["total_invocations"] * 50000)
        self.assertTrue(est["fits_budget"])
        self.ok(run("run.py", "set-budget", str(self.run_dir), "2"))
        self.assertFalse(self.ok(run("ledger.py", "estimate", str(self.run_dir)))["fits_budget"])
        out = self.ok(run("ledger.py", "defer", str(self.run_dir), "--reason", "budget_cannot_reserve_critics_and_validation", "--all-planned"))
        self.assertEqual(len(out["deferred"]), 2)
        self.assertTrue(all(u["status"] == "deferred" and u["unresolved"] for u in self.ledger()))
        self.ok(run("ledger.py", "validate", str(self.run_dir)))


class FindingsTests(RunFixture):
    def test_add_decide_and_validate(self) -> None:
        self.hunt()
        u1, _ = self.unit_ids()
        fp = "app/files.py:read_user_file:path-traversal"
        self.refused(run("ledger.py", "decide", str(self.run_dir), "--fingerprint", fp, "--verdict", "confirmed"), "add the record with findings.py first")
        rec = self.write_json(self.candidate_record(0), "confirmed.json")
        out = self.ok(run("findings.py", "add", str(self.run_dir), str(rec), "--target", str(self.target)))
        self.assertEqual(out["records"], 1)
        self.refused(run("findings.py", "add", str(self.run_dir), str(rec)), "pass --replace")
        self.refused(run("ledger.py", "decide", str(self.run_dir), "--fingerprint", fp, "--verdict", "rejected"), "says confirmed, not rejected")
        out = self.ok(run("ledger.py", "decide", str(self.run_dir), "--fingerprint", fp, "--verdict", "confirmed"))
        self.assertEqual(out["units"], [u1])
        self.assertEqual(out["pending"], 2)
        nv = self.write_json(self.candidate_record(1), "nv.json")
        self.ok(run("findings.py", "add", str(self.run_dir), str(nv)))
        self.ok(run("ledger.py", "decide", str(self.run_dir), "--fingerprint", "app/files.py:read_user_file:symlink-escape", "--verdict", "needs_validation"))
        self.ok(run("findings.py", "add", str(self.run_dir), str(self.fill("record-rejected.json"))))
        out = self.ok(run("ledger.py", "decide", str(self.run_dir), "--fingerprint", "app/files.py:list_user_files:enumeration", "--verdict", "rejected"))
        self.assertEqual(out["pending"], 0)
        unit = next(u for u in self.ledger() if u["coverage_id"] == u1)
        self.assertEqual(set(unit["decisions"].values()), {"confirmed", "needs_validation", "rejected"})
        out = self.ok(run("findings.py", "validate", str(self.run_dir), "--target", str(self.target)))
        self.assertEqual(out["verdicts"], {"confirmed": 1, "needs_validation": 1, "rejected": 1})
        findings = json.loads((self.run_dir / "findings.json").read_text(encoding="utf-8"))
        self.assertEqual([r["fingerprint"] for r in findings], sorted(r["fingerprint"] for r in findings))

    def test_add_refuses_a_stale_record(self) -> None:
        self.hunt()
        (self.target / "app" / "files.py").write_text("# changed\n", encoding="utf-8")
        rec = self.write_json(self.candidate_record(0), "stale.json")
        self.refused(run("findings.py", "add", str(self.run_dir), str(rec), "--target", str(self.target)), "cited source changed")

    def test_replace_keeps_one_record_per_fingerprint(self) -> None:
        self.hunt()
        rec = self.candidate_record(0)
        self.ok(run("findings.py", "add", str(self.run_dir), str(self.write_json(rec, "a.json"))))
        rec["severity"]["overall"] = "medium"
        out = self.ok(run("findings.py", "add", str(self.run_dir), str(self.write_json(rec, "b.json")), "--replace"))
        self.assertEqual((out["replaced"], out["records"]), ("confirmed", 1))

    def test_note_appends_to_notes_json(self) -> None:
        out = self.ok(run("findings.py", "note", str(self.run_dir), "--agent", "verifier-1", "--kind", "hardening", "--text", "pin the test runner version"))
        self.assertEqual(out["notes"], 1)
        self.refused(run("findings.py", "note", str(self.run_dir), "--agent", "Verifier", "--kind", "hardening", "--text", "x"), "canonical agent id")


class PriorRunTests(RunFixture):
    def complete_run(self) -> None:
        self.hunt()
        for i in (0, 1):
            self.ok(run("findings.py", "add", str(self.run_dir), str(self.write_json(self.candidate_record(i), f"r{i}.json"))))
        self.ok(run("findings.py", "add", str(self.run_dir), str(self.fill("record-rejected.json"))))
        for fp, v in (("app/files.py:read_user_file:path-traversal", "confirmed"), ("app/files.py:read_user_file:symlink-escape", "needs_validation"), ("app/files.py:list_user_files:enumeration", "rejected")):
            self.ok(run("ledger.py", "decide", str(self.run_dir), "--fingerprint", fp, "--verdict", v))
        self.ok(run("run.py", "set-status", str(self.run_dir), "complete"))

    def test_same_source_carries_records_and_suppresses_rejected(self) -> None:
        self.complete_run()
        run2 = self.tmpdir / "out" / "run-2"
        self.ok(run("run.py", "init", "--target", str(self.target), "--output", str(run2), "--prior", str(self.run_dir)))
        out = self.ok(run("ledger.py", "seed", str(run2), "--target", str(self.target), "--units", str(FIXTURES / "units.json"), "--prior", str(self.run_dir)))
        self.assertEqual(sorted(out["carried"]), ["app/files.py:read_user_file:path-traversal", "app/files.py:read_user_file:symlink-escape"])
        self.assertEqual(out["suppressed"], ["app/files.py:list_user_files:enumeration"])
        units = {u["attack_class"]: u for u in json.loads((run2 / "coverage-ledger.json").read_text(encoding="utf-8"))}
        self.assertEqual(units["Resource and file handling"]["prior_status"], "prior_confirmed_same_source")
        self.assertEqual(units["Injection"]["prior_status"], "prior_covered_same_source")
        cands = json.loads((run2 / "candidates.json").read_text(encoding="utf-8"))
        self.assertTrue(all(r["carried_from"] == "run-1" for r in cands["carried"]))
        # the verifier re-checks a carried record: add then decide with --agent links the planned unit
        rec = self.candidate_record(0)
        self.ok(run("findings.py", "add", str(run2), str(self.write_json(rec, "carried.json"))))
        self.refused(run("ledger.py", "decide", str(run2), "--fingerprint", rec["fingerprint"], "--verdict", "confirmed"), "needs --agent")
        out = self.ok(run("ledger.py", "decide", str(run2), "--fingerprint", rec["fingerprint"], "--verdict", "confirmed", "--agent", "verifier-1"))
        unit = next(u for u in json.loads((run2 / "coverage-ledger.json").read_text(encoding="utf-8")) if u["coverage_id"] == out["units"][0])
        self.assertEqual((unit["status"], unit["agent_id"]), ("candidate", "verifier-1"))

    def test_changed_source_revalidates_instead_of_carrying(self) -> None:
        self.complete_run()
        path = self.target / "app" / "files.py"
        path.write_text(path.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8")
        run2 = self.tmpdir / "out" / "run-2"
        self.ok(run("run.py", "init", "--target", str(self.target), "--output", str(run2), "--prior", str(self.run_dir)))
        out = self.ok(run("ledger.py", "seed", str(run2), "--target", str(self.target), "--units", str(FIXTURES / "units.json"), "--prior", str(self.run_dir)))
        self.assertEqual(out["carried"], [])
        self.assertEqual(out["suppressed"], [])
        units = {u["attack_class"]: u for u in json.loads((run2 / "coverage-ledger.json").read_text(encoding="utf-8"))}
        self.assertEqual(units["Resource and file handling"]["prior_status"], "prior_confirmed_changed_source")
        self.assertEqual(units["Injection"]["prior_status"], "prior_covered_changed_source")
        cands = json.loads((run2 / "candidates.json").read_text(encoding="utf-8"))
        self.assertEqual(cands["carried"], [])


class CompileTests(RunFixture):
    def reports(self) -> dict[str, str]:
        self.hunt()
        for i in (0, 1):
            self.ok(run("findings.py", "add", str(self.run_dir), str(self.write_json(self.candidate_record(i), f"r{i}.json"))))
        self.ok(run("findings.py", "add", str(self.run_dir), str(self.fill("record-rejected.json"))))
        for fp, v in (("app/files.py:read_user_file:path-traversal", "confirmed"), ("app/files.py:read_user_file:symlink-escape", "needs_validation"), ("app/files.py:list_user_files:enumeration", "rejected")):
            self.ok(run("ledger.py", "decide", str(self.run_dir), "--fingerprint", fp, "--verdict", v))
        out = self.ok(run("compile.py", str(self.run_dir)))
        self.assertEqual(out["confirmed"], 1)
        return {n: (self.run_dir / n).read_text(encoding="utf-8") for n in out["written"]}

    def test_reports_derive_from_records(self) -> None:
        reports = self.reports()
        ja, en = reports["REPORT.ja.md"], reports["REPORT.md"]
        self.assertIn("# code-audit 報告書: target", ja)
        self.assertIn("# code-audit report: target", en)
        for text in (ja, en):
            self.assertIn("| high | Path traversal in read_user_file |", text)
            self.assertIn("source (reading only)" if text is en else "source（読解のみ）", text)
            self.assertIn("app/files.py:read_user_file:path-traversal", text)
            self.assertIn("app/files.py:list_user_files:enumeration", text)
            self.assertNotIn(str(self.tmpdir), text)
            self.assertIn("covered 1", text)
            self.assertIn("Makefile#fetch", text)
        self.assertIn("Hardening notes (not findings)", en)
        self.assertIn("read_user_file could refuse absolute names", en)
        nv_en = reports["NEEDS-VALIDATION.md"]
        self.assertIn("Symlink inside base_dir may escape it", nv_en)
        self.assertIn("the owner checks who can write inside", nv_en)
        self.assertNotIn("**Severity", nv_en)
        self.assertNotIn("overall", nv_en)
        self.assertNotIn("list_user_files reveals", nv_en)

    def test_code_stays_inside_fences(self) -> None:
        reports = self.reports()
        fixed = self.candidate_record(0)["remediation"]["code_changes"][0]["fixed_code"].split("\n")
        for name in ("REPORT.ja.md", "REPORT.md"):
            inside = False
            seen_inside = 0
            for line in reports[name].splitlines():
                if line.startswith("````"):
                    inside = not inside
                    continue
                if line in fixed:
                    self.assertTrue(inside, f"{name}: code line outside a fence: {line}")
                    seen_inside += 1
            self.assertFalse(inside, f"{name}: unclosed fence")
            self.assertEqual(seen_inside, len(fixed))

    def test_incomplete_and_quick_runs_say_so(self) -> None:
        self.ok(run("run.py", "set-status", str(self.run_dir), "incomplete", "--reason", "validation_budget_exhausted"))
        self.ok(run("compile.py", str(self.run_dir)))
        en = (self.run_dir / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("This run is a partial pass.", en)
        self.assertIn("validation_budget_exhausted", en)
        self.assertIn("No confirmed findings.", en)


class ClassesTests(unittest.TestCase):
    def test_list_parses_headings_and_sources(self) -> None:
        proc = run("classes.py", "list", "--classes", str(FIXTURES / "classes"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        classes = json.loads(proc.stdout)
        self.assertEqual([c["name"] for c in classes], ["Path confinement after resolution", "Writes outside the declared work directory"])
        self.assertEqual(classes[1]["sources"], ["ADR-021", "security.md#A check that refuses places must not write to test them"])

    def test_check_knowledge_verifies_headings(self) -> None:
        proc = run("classes.py", "check-knowledge", "--classes", str(FIXTURES / "classes"), "--knowledge", str(FIXTURES / "knowledge"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual((out["sources_checked"], out["adr_unchecked"]), (2, 1))
        proc = run("classes.py", "check-knowledge", "--classes", str(FIXTURES / "classes"), "--knowledge", str(FIXTURES / "knowledge"), "--adr", str(FIXTURES / "adr"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["adr_unchecked"], 0)

    def test_check_knowledge_fails_on_a_missing_heading_or_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            classes = Path(tmp) / "classes"
            classes.mkdir()
            (classes / "x.md").write_text("## Lonely class\nSource: security.md#No such heading\n\nbody\n\n## Unsourced\n\nbody\n", encoding="utf-8")
            proc = run("classes.py", "check-knowledge", "--classes", str(classes), "--knowledge", str(FIXTURES / "knowledge"))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("heading not found", proc.stderr)
            self.assertIn("needs a Source: line", proc.stderr)

    def test_size_limit(self) -> None:
        proc = run("classes.py", "size", "--classes", str(FIXTURES / "classes"), "--max-bytes", "8192")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = run("classes.py", "size", "--classes", str(FIXTURES / "classes"), "--max-bytes", "10")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("exceeds 10", proc.stderr)

    def test_shipped_classes_pass_when_present(self) -> None:
        shipped = SKILL / "classes"
        if not shipped.is_dir():
            self.skipTest("classes/ not written yet (Phase 1 cut 2)")
        proc = run("classes.py", "size", "--classes", str(shipped))
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], "-v"])
