#!/usr/bin/env python3
"""Derive the human-facing reports of a code-audit run (stdlib only).

Usage:
    compile.py <run-dir>

Writes REPORT.ja.md, REPORT.md, NEEDS-VALIDATION.ja.md and
NEEDS-VALIDATION.md from run-metadata.json, coverage-ledger.json,
findings.json, candidates.json and notes.json. Prose never changes a verdict,
a severity, a blocker or an observed result: every value in the report is
copied from a record. Code and payloads appear only inside fenced blocks.
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _contract as c  # noqa: E402

FENCE = "````"
SEVERITY_RANK = {s: i for i, s in enumerate(reversed(c.IMPACT_ORDER))}

L = {
    "ja": {
        "title": "code-audit 報告書",
        "run": "実行の事実",
        "run_id": "run_id", "repo": "リポジトリ", "source_ref": "source ref", "dirty": "作業ツリーに未コミットの変更", "profile": "プロファイル",
        "budget": "予算（呼び出し回数）", "invocations": "実績の呼び出し回数", "status": "run_status", "prior": "持ち越した過去の実行", "policy": "実行方針", "created": "開始", "replacements": "再検証で置換したレコード", "replacements_value": "{n} 件（うち強化 {s} 件、いずれも別の新しい検証者が確認）",
        "yes": "あり", "no": "なし", "none": "なし", "unset": "未設定", "th_item": "項目", "th_value": "値",
        "partial": "この実行は部分的な網羅です。",
        "partial_quick": "quick プロファイルはハンター 1 波と批評 1 回の事前宣言された早期終了であり、網羅の完了を意味しません。",
        "partial_incomplete": "run_status は incomplete です。理由: {reason}",
        "posture": "要約",
        "posture_line": "confirmed {confirmed} 件（critical {critical} / high {high} / medium {medium} / low {low} / informational {informational}）、needs_validation {nv} 件、rejected {rejected} 件。",
        "coverage_line": "網羅単位 {units} 件: covered {covered} / candidate {candidate}（うち判定済 {candidate_decided}）/ blocked {blocked} / deferred {deferred} / out_of_scope {out_of_scope} / planned {planned}。",
        "confirmed": "確定した所見", "confirmed_none": "確定した所見はありません。",
        "th_sev": "深刻度", "th_title": "題名", "th_boundary": "境界", "th_kind": "根拠種別", "th_observed": "観測された結果",
        "kind_source": "source（読解のみ）", "kind_test": "existing_test（{log}）",
        "fingerprint": "fingerprint", "description": "説明", "root_cause": "根本原因", "intended": "意図された振る舞い",
        "trace": "経路", "evidence": "根拠", "conditions": "条件", "evidence_kind": "根拠種別", "observed": "観測された結果",
        "severity": "深刻度", "likelihood": "起こりやすさ", "impact": "影響", "overall": "総合", "confidence": "確信度",
        "remediation": "修正", "strategy": "方針", "code_changes": "修正案", "coverage_ids": "網羅単位",
        "nv": "検証待ちの手がかり", "nv_none": "検証待ちの手がかりはありません。",
        "nv_intro": "深刻度は付けません。各項目は未解決の事実と、それを解く安全な手順です。詳細は NEEDS-VALIDATION.ja.md。",
        "th_blockers": "未解決の事実", "th_local": "手元での確認", "th_deploy": "配備側で観測する確認", "claimed": "主張された根本原因", "blockers": "未解決の事実", "plan": "確認の手順",
        "local": "手元", "deployment": "配備側",
        "notes": "覚え書き", "hardening": "強化の提案（所見ではない）", "out_of_scope": "範囲外の観察", "lead": "次の実行への手がかり（判定なし。次回の `seed --prior` が批評者に渡す）", "prior_leads": "前回の実行から渡された手がかり（この実行の批評者が見た）",
        "coverage": "網羅の要約", "th_status": "状態", "th_count": "件数", "deferred_units": "先送り・範囲外の単位と理由", "uncovered": "次の波に回すべき未割当の面", "unverified": "検証に至らなかった候補（判定なし・深刻度なし）", "undecided": "台帳の判定が無いレコード（所見として報告しない）", "unlinked_prior": "今回の単位に結び付かない前回のレコード（判定なし）", "changed_prior": "引用元が変わったため持ち越さず再度狩った前回のレコード（今回の判定は上の表）",
        "rejected": "反証された候補", "rejected_line": "反証された候補は所見ではありません。次回の再報告を抑えるために fingerprint だけを記します: {fps}",
        "merged": "同根として統合した候補", "merged_line": "次の候補は別の fingerprint と根本原因を共有すると判断し、統合先で 1 回だけ検証しました（統合先の判定が上の表にあります）。",
        "carried": "持ち越し", "suppressed": "前回 rejected のまま抑止した主張",
        "nv_title": "code-audit 検証待ちの手がかり",
    },
    "en": {
        "title": "code-audit report",
        "run": "Run facts",
        "run_id": "run_id", "repo": "repository", "source_ref": "source ref", "dirty": "uncommitted changes in the worktree", "profile": "profile",
        "budget": "budget (invocations)", "invocations": "actual invocations", "status": "run_status", "prior": "prior runs carried", "policy": "execution policy", "created": "started", "replacements": "records replaced after re-verification", "replacements_value": "{n} ({s} strengthening, each confirmed by a second fresh verifier)",
        "yes": "yes", "no": "no", "none": "none", "unset": "unset", "th_item": "Item", "th_value": "Value",
        "partial": "This run is a partial pass.",
        "partial_quick": "The quick profile is a pre-declared early stop (one hunter wave, one critic) and is not evidence of complete coverage.",
        "partial_incomplete": "run_status is incomplete. Reason: {reason}",
        "posture": "Summary",
        "posture_line": "{confirmed} confirmed (critical {critical} / high {high} / medium {medium} / low {low} / informational {informational}), {nv} needs_validation, {rejected} rejected.",
        "coverage_line": "{units} coverage units: covered {covered} / candidate {candidate} ({candidate_decided} decided) / blocked {blocked} / deferred {deferred} / out_of_scope {out_of_scope} / planned {planned}.",
        "confirmed": "Confirmed findings", "confirmed_none": "No confirmed findings.",
        "th_sev": "Severity", "th_title": "Title", "th_boundary": "Boundary", "th_kind": "Evidence kind", "th_observed": "Observed result",
        "kind_source": "source (reading only)", "kind_test": "existing_test ({log})",
        "fingerprint": "fingerprint", "description": "Description", "root_cause": "Root cause", "intended": "Intended behaviour",
        "trace": "Trace", "evidence": "Evidence", "conditions": "Conditions", "evidence_kind": "Evidence kind", "observed": "Observed result",
        "severity": "Severity", "likelihood": "likelihood", "impact": "impact", "overall": "overall", "confidence": "Confidence",
        "remediation": "Remediation", "strategy": "strategy", "code_changes": "proposed changes", "coverage_ids": "coverage units",
        "nv": "Needs validation", "nv_none": "No leads awaiting validation.",
        "nv_intro": "No severity is assigned. Each lead names the unresolved fact and a safe step to settle it. Details in NEEDS-VALIDATION.md.",
        "th_blockers": "Unresolved facts", "th_local": "Local check", "th_deploy": "Owner-observed check", "claimed": "Claimed root cause", "blockers": "Unresolved facts", "plan": "Validation plan",
        "local": "local", "deployment": "deployment",
        "notes": "Notes", "hardening": "Hardening notes (not findings)", "out_of_scope": "Out-of-scope observations", "lead": "Leads for the next run (no verdict; the next run's `seed --prior` hands them to its critic)", "prior_leads": "Leads handed over from prior runs (seen by this run's critic)",
        "coverage": "Coverage summary", "th_status": "Status", "th_count": "Count", "deferred_units": "Deferred and out-of-scope units with reasons", "uncovered": "Unassigned surfaces for a later wave", "unverified": "Candidates not verified (no verdict, no severity)", "undecided": "Records without a ledger decision (not reported as findings)", "unlinked_prior": "Prior records that no current unit covers (no verdict)", "changed_prior": "Prior records whose cited sources changed (re-hunted, not carried; this run's verdicts are above)",
        "rejected": "Rejected candidates", "rejected_line": "Rejected candidates are not findings. Only their fingerprints are listed so the next run does not repeat the claim: {fps}",
        "merged": "Candidates merged as duplicates", "merged_line": "These candidates were judged to share a root cause with another fingerprint and were verified once under it (the kept fingerprint's verdict is in the tables above).",
        "carried": "carried", "suppressed": "claims suppressed as rejected in a prior run",
        "nv_title": "code-audit leads awaiting validation",
    },
}


def plain(text: object) -> str:
    """Prose for a Markdown line or cell: one line, no control or format
    character (terminal escapes, C1 controls, bidirectional overrides,
    zero-width characters all go), no fence, no table break. Made inert here,
    once, for everything the report prints — never at each print site."""
    s = "".join(ch for ch in str(text) if not unicodedata.category(ch).startswith("C") or ch in "\n\t")
    s = " ".join(s.split())
    return s.replace("```", "` ` `").replace("|", "\\|")


def code(text: object) -> str:
    """A value placed inside an inline code span: plain, and no backtick, so
    the value cannot close the span and start Markdown of its own."""
    return plain(text).replace("`", "'")


def fenced(code: str, lang: str = "") -> list[str]:
    body = code.replace(FENCE, "` ` ` `")
    return [f"{FENCE}{lang}", *body.rstrip("\n").split("\n"), FENCE, ""]


def table(headers: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    out.append("")
    return out


def boundary_of(rec: dict, units: dict) -> str:
    for cid in rec.get("coverage_ids", []):
        u = units.get(cid)
        if u:
            return u["boundary"]
    return "-"


def kind_label(rec: dict, t: dict) -> str:
    if rec["evidence_kind"] == "existing_test":
        return t["kind_test"].format(log=rec["check_log"])
    return t["kind_source"]


def render_report(lang: str, meta: dict, units: list, findings: list, candidates: dict, notes: list, replacements: list | None = None) -> str:
    replacements = replacements or []
    t = L[lang]
    uid = {u["coverage_id"]: u for u in units}
    decided = {d["fingerprint"]: d["verdict"] for d in candidates.get("decided", [])}
    undecided = [r for r in findings if decided.get(r["fingerprint"]) != r["verdict"]]
    findings = [r for r in findings if decided.get(r["fingerprint"]) == r["verdict"]]
    confirmed = sorted((r for r in findings if r["verdict"] == "confirmed"), key=lambda r: (SEVERITY_RANK[r["severity"]["overall"]], r["fingerprint"]))
    nv = [r for r in findings if r["verdict"] == "needs_validation"]
    rejected = [r for r in findings if r["verdict"] == "rejected"]
    counts: dict[str, int] = {}
    for u in units:
        counts[u["status"]] = counts.get(u["status"], 0) + 1
    out: list[str] = [f"# {t['title']}: {plain(meta['repo'])}", ""]

    out.append(f"## {t['run']}")
    out.append("")
    inv = meta["invocations"]
    rows = [
        [t["run_id"], plain(meta["run_id"])],
        [t["repo"], plain(meta["repo"])],
        [t["source_ref"], plain(meta["source_ref"])],
        [t["dirty"], t["yes"] if meta["dirty"] else t["no"]],
        [t["profile"], meta["profile"]],
        [t["budget"], str(meta["budget"]) if meta["budget"] is not None else t["unset"]],
        [t["invocations"], f"{sum(inv.values())} (" + ", ".join(f"{k} {v}" for k, v in inv.items()) + ")"],
        [t["status"], meta["run_status"]],
        [t["prior"], ", ".join(plain(p) for p in meta["prior_runs"]) or t["none"]],
        [t["policy"], meta["execution_policy"]],
        [t["created"], plain(meta["created"])],
    ]
    if replacements:
        strong = sum(1 for r in replacements if r.get("strengthened"))
        rows.append([t["replacements"], t["replacements_value"].format(n=len(replacements), s=strong)])
    out += table([t["th_item"], t["th_value"]], rows)
    partial = []
    if meta["profile"] == "quick":
        partial.append(t["partial_quick"])
    if meta["run_status"] == "incomplete":
        partial.append(t["partial_incomplete"].format(reason=plain(meta["incomplete_reason"] or "")))
    if partial:
        out.append("**" + t["partial"] + "** " + " ".join(partial))
        out.append("")

    out.append(f"## {t['posture']}")
    out.append("")
    sev_counts = {s: sum(1 for r in confirmed if r["severity"]["overall"] == s) for s in c.IMPACT_ORDER}
    out.append(t["posture_line"].format(confirmed=len(confirmed), nv=len(nv), rejected=len(rejected), **sev_counts))
    candidate_decided = sum(1 for u in units if u["status"] == "candidate" and u["result_fingerprints"] and all(fp in decided for fp in u["result_fingerprints"]))
    out.append(t["coverage_line"].format(units=len(units), candidate_decided=candidate_decided, **{s: counts.get(s, 0) for s in ("covered", "candidate", "blocked", "deferred", "out_of_scope", "planned")}))
    out.append("")

    out.append(f"## {t['confirmed']}")
    out.append("")
    if not confirmed:
        out.append(t["confirmed_none"])
        out.append("")
    else:
        out += table([t["th_sev"], t["th_title"], t["th_boundary"], t["th_kind"], t["th_observed"]],
                     [[r["severity"]["overall"], plain(r["title"]), plain(boundary_of(r, uid)), plain(kind_label(r, t)), plain(r["observed_result"])] for r in confirmed])
        for r in confirmed:
            out.append(f"### [{r['severity']['overall']}] {plain(r['title'])}")
            out.append("")
            out.append(f"- {t['fingerprint']}: `{code(r['fingerprint'])}`")
            out.append(f"- {t['evidence_kind']}: {plain(kind_label(r, t))}")
            out.append(f"- {t['coverage_ids']}: " + ", ".join(f"`{code(x)}`" for x in r["coverage_ids"]))
            out.append("")
            out.append(f"**{t['description']}.** {plain(r['description'])}")
            out.append("")
            out.append(f"**{t['root_cause']}.** {plain(r['root_cause'])}")
            out.append("")
            out.append(f"**{t['intended']}.** {plain(r['intended_behavior'])}")
            out.append("")
            out.append(f"**{t['trace']}.**")
            out.append("")
            for i, s in enumerate(r["trace"], start=1):
                out.append(f"{i}. `{code(s['file'])}:{s['line']}` ({s['kind']}, {plain(s['scope'])}) — {plain(s['description'])}")
            out.append("")
            out.append(f"**{t['evidence']}.**")
            out.append("")
            for e in r["evidence"]:
                out.append(f"- `{code(e['file'])}:{e['line']}` — {plain(e['description'])}")
            out.append("")
            if r["conditions"]:
                out.append(f"**{t['conditions']}.**")
                out.append("")
                for cond in r["conditions"]:
                    out.append(f"- {plain(cond['kind'])}: {plain(cond['description'])}")
                out.append("")
            out.append(f"**{t['observed']}.** {plain(r['observed_result'])}")
            out.append("")
            sev = r["severity"]
            out.append(f"**{t['severity']}.** {t['likelihood']} {sev['likelihood']['score']} ({plain(sev['likelihood']['reason'])}); {t['impact']} {sev['impact']['score']} ({plain(sev['impact']['reason'])}); {t['overall']} **{sev['overall']}**.")
            out.append("")
            out.append(f"**{t['confidence']}.** {r['confidence']['score']} ({plain(r['confidence']['reason'])})")
            out.append("")
            out.append(f"**{t['remediation']}.** {plain(r['remediation']['strategy'])}")
            out.append("")
            for chg in r["remediation"]["code_changes"]:
                out.append(f"{t['code_changes']}: `{code(chg['file_name'])}`")
                out.append("")
                out += fenced(chg["fixed_code"])

    out.append(f"## {t['nv']}")
    out.append("")
    if not nv:
        out.append(t["nv_none"])
        out.append("")
    else:
        out.append(t["nv_intro"])
        out.append("")
        out += table([t["th_title"], t["trace"], t["th_blockers"], t["th_local"], t["th_deploy"]],
                     [[plain(r["title"]), plain(f"{r['trace'][0]['file']}:{r['trace'][0]['line']}"), plain("; ".join(r["blockers"])), plain(r["validation_plan"].get("local", "") or "-"), plain(r["validation_plan"].get("deployment", "") or "-")] for r in nv])

    hard = [n for n in notes if n.get("kind") == "hardening"]
    oos = [n for n in notes if n.get("kind") == "out_of_scope"]
    leads = [n for n in notes if n.get("kind") == "lead"]
    prior_leads = candidates.get("prior_leads", [])
    if hard or oos or leads or prior_leads:
        out.append(f"## {t['notes']}")
        out.append("")
        if leads:
            out.append(f"### {t['lead']}")
            out.append("")
            for n in leads:
                out.append(f"- {plain(n['text'])}")
            out.append("")
        if prior_leads:
            out.append(f"### {t['prior_leads']}")
            out.append("")
            for n in prior_leads:
                out.append(f"- ({plain(str(n.get('prior_run', '')))}) {plain(n['text'])}")
            out.append("")
        if hard:
            out.append(f"### {t['hardening']}")
            out.append("")
            for n in hard:
                out.append(f"- {plain(n['text'])}")
            out.append("")
        if oos:
            out.append(f"### {t['out_of_scope']}")
            out.append("")
            for n in oos:
                out.append(f"- {plain(n['text'])}")
            out.append("")

    out.append(f"## {t['coverage']}")
    out.append("")
    out += table([t["th_status"], t["th_count"]], [[s, str(n)] for s, n in sorted(counts.items())])
    reasoned = [u for u in units if u["status"] in ("deferred", "out_of_scope", "not_applicable")]
    if reasoned:
        out.append(f"### {t['deferred_units']}")
        out.append("")
        for u in reasoned:
            out.append(f"- `{code(u['coverage_id'])}` ({u['status']}): {plain('; '.join(u['unresolved']))}")
        out.append("")
    if undecided:
        out.append(f"### {t['undecided']}")
        out.append("")
        for r in undecided:
            out.append(f"- `{code(r['fingerprint'])}`: {plain(r.get('title', ''))}")
        out.append("")
    if candidates.get("changed_prior"):
        out.append(f"### {t['changed_prior']}")
        out.append("")
        for r in candidates["changed_prior"]:
            out.append(f"- `{code(r['fingerprint'])}` ({plain(r['prior_run'])}, {plain(r['verdict'])}): {plain(r.get('title', ''))}")
        out.append("")
    if candidates.get("unlinked_prior"):
        out.append(f"### {t['unlinked_prior']}")
        out.append("")
        for r in candidates["unlinked_prior"]:
            out.append(f"- `{code(r['fingerprint'])}` ({plain(r['prior_run'])}, {plain(r['verdict'])}): {plain(r.get('title', ''))}")
        out.append("")
    pending = list(candidates.get("candidates", [])) + list(candidates.get("carried", []))
    if pending:
        out.append(f"### {t['unverified']}")
        out.append("")
        for r in pending:
            out.append(f"- `{code(r['fingerprint'])}`: {plain(r.get('title', ''))}")
        out.append("")
    if candidates.get("uncovered"):
        out.append(f"### {t['uncovered']}")
        out.append("")
        for x in candidates["uncovered"]:
            out.append(f"- {plain(x['surface'])} / {plain(x['boundary'])} / {plain(x['attack_class'])}: {plain(x['reason'])}")
        out.append("")
    if candidates.get("suppressed"):
        out.append(f"### {t['suppressed']}")
        out.append("")
        for s in candidates["suppressed"]:
            out.append(f"- `{code(s['fingerprint'])}`")
        out.append("")
    if rejected:
        out.append(f"## {t['rejected']}")
        out.append("")
        out.append(t["rejected_line"].format(fps=", ".join(f"`{code(r['fingerprint'])}`" for r in rejected)))
        out.append("")
    if candidates.get("merged"):
        out.append(f"## {t['merged']}")
        out.append("")
        out.append(t["merged_line"])
        out.append("")
        for m in candidates["merged"]:
            out.append(f"- `{code(m['fingerprint'])}` → `{code(m['into'])}`: {plain(m.get('reason', ''))}")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def decided_only(findings: list, candidates: dict) -> list:
    decided = {d["fingerprint"]: d["verdict"] for d in candidates.get("decided", [])}
    return [r for r in findings if decided.get(r["fingerprint"]) == r["verdict"]]


def render_needs_validation(lang: str, meta: dict, findings: list) -> str:
    t = L[lang]
    nv = sorted((r for r in findings if r["verdict"] == "needs_validation"), key=lambda r: r["fingerprint"])
    out = [f"# {t['nv_title']}: {plain(meta['repo'])}", "", t["nv_intro"].split("。")[0].split(". ")[0] + ".", ""]
    if not nv:
        out.append(t["nv_none"])
        out.append("")
    for r in nv:
        out.append(f"## {plain(r['title'])}")
        out.append("")
        out.append(f"- {t['fingerprint']}: `{code(r['fingerprint'])}`")
        out.append(f"- {t['coverage_ids']}: " + ", ".join(f"`{code(x)}`" for x in r["coverage_ids"]))
        if r.get("carried_from"):
            out.append(f"- {t['carried']}: `{code(r['carried_from'])}`")
        out.append("")
        out.append(f"**{t['description']}.** {plain(r['description'])}")
        out.append("")
        out.append(f"**{t['claimed']}.** {plain(r['claimed_root_cause'])}")
        out.append("")
        out.append(f"**{t['trace']}.**")
        out.append("")
        for i, s in enumerate(r["trace"], start=1):
            out.append(f"{i}. `{code(s['file'])}:{s['line']}` ({s['kind']}, {plain(s['scope'])}) — {plain(s['description'])}")
        out.append("")
        out.append(f"**{t['evidence']}.**")
        out.append("")
        for e in r["evidence"]:
            out.append(f"- `{code(e['file'])}:{e['line']}` — {plain(e['description'])}")
        out.append("")
        out.append(f"**{t['blockers']}.**")
        out.append("")
        for b in r["blockers"]:
            out.append(f"- {plain(b)}")
        out.append("")
        out.append(f"**{t['plan']}.**")
        out.append("")
        for k in ("local", "deployment"):
            if str(r["validation_plan"].get(k, "")).strip():
                out.append(f"- {t[k]}: {plain(r['validation_plan'][k])}")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir")
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    meta = c.load_metadata(run_dir)
    ledger_path = run_dir / c.LEDGER_FILE
    units = c.read_json(ledger_path) if ledger_path.exists() else []
    findings = c.load_findings(run_dir)
    candidates = c.load_candidates(run_dir)
    notes = c.load_notes(run_dir)
    replacements = c.load_replacements(run_dir)
    written = []
    for lang, name, nv_name in (("ja", "REPORT.ja.md", "NEEDS-VALIDATION.ja.md"), ("en", "REPORT.md", "NEEDS-VALIDATION.md")):
        (run_dir / name).write_text(render_report(lang, meta, units, findings, candidates, notes, replacements), encoding="utf-8")
        (run_dir / nv_name).write_text(render_needs_validation(lang, meta, decided_only(findings, candidates)), encoding="utf-8")
        written += [name, nv_name]
    reported = decided_only(findings, candidates)
    c.emit({"written": written, "confirmed": sum(1 for r in reported if r["verdict"] == "confirmed"), "needs_validation": sum(1 for r in reported if r["verdict"] == "needs_validation"), "rejected": sum(1 for r in reported if r["verdict"] == "rejected"), "undecided": len(findings) - len(reported)})


if __name__ == "__main__":
    main()
