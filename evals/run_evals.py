"""Run the 12 eval cases and print a pass rate.

    python -m evals.run_evals          # all cases
    python -m evals.run_evals --json   # machine-readable

Checks:
  production-report  every number matches totals summed independently by the seed script;
                     the narrative has no number that did not come from code
  quote-intake       lines and missing fields are exactly as expected; no field fails the source check
  customer-reply     every fact sentence cites a real FAQ entry; unsupported sentences are replaced
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from agency import config, services, skill_runner

CASES = Path(__file__).resolve().parent / "cases.json"


def _close(a, b) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) < 0.005


def check_numbers(case: dict) -> list[str]:
    report = skill_runner.report().compute(config.ROOT / case["input"])
    exp = json.loads((config.ROOT / case["expected"]).read_text())
    t, problems = report["totals"], []
    for key in ("total_premium", "policies_written", "new_policies", "renewal_policies", "retention_rate", "pct_of_target"):
        if not _close(t[key], exp[key]):
            problems.append(f"{key}: report {t[key]} vs expected {exp[key]}")
    for row in report["by_line"]:
        e = exp["by_line"][row["line"]]
        if row["policies"] != e["policies"] or not _close(row["premium"], e["premium"]):
            problems.append(f"{row['line']}: report {row['policies']} / {row['premium']} vs expected {e['policies']} / {e['premium']}")
    for row in report["by_producer"]:
        e = exp["by_producer"][row["producer"]]
        if not _close(row["premium"], e["premium"]) or not _close(row["pct_of_target"], e["pct_of_target"]):
            problems.append(f"{row['producer']}: report {row['premium']} vs expected {e['premium']}")
    if "expect_skipped" in case and report["source"]["rows_skipped"] != case["expect_skipped"]:
        problems.append(f"rows skipped: {report['source']['rows_skipped']} vs expected {case['expect_skipped']}")
    return problems


def check_narrative(case: dict) -> list[str]:
    out = services.run_report(config.ROOT / case["input"])
    problems = list(out["problems"])
    text = out["headline"] + " " + " ".join(out["paragraphs"])
    if "{{" in text:
        problems.append("unfilled placeholder left in the narrative")
    if not out["paragraphs"]:
        problems.append("no narrative")
    if case.get("expect_flag") and case["expect_flag"] not in [f["id"] for f in out["report"]["flags"]]:
        problems.append(f"expected flag {case['expect_flag']} not raised")
    return problems


def check_quote(case: dict) -> list[str]:
    out = services.run_intake((config.ROOT / case["input"]).read_text())
    res, problems = out["result"], []
    if sorted(res["lines"]) != sorted(case["expect_lines"]):
        problems.append(f"lines {res['lines']} vs expected {case['expect_lines']}")
    missing = sorted(m["key"] for m in res["missing"])
    if missing != sorted(case["expect_missing"]):
        problems.append(f"missing {missing} vs expected {sorted(case['expect_missing'])}")
    for r in res["rejected"]:
        problems.append(f"field {r['key']} failed the source check: {r['reason']}")
    return problems


def check_reply(case: dict) -> list[str]:
    out = services.run_reply((config.ROOT / case["input"]).read_text())
    res, problems = out["result"], []
    faq = services.faq()
    for s in res["sentences"]:
        if s["type"] == "fact" and not s["faq_ids"]:
            problems.append(f"uncited fact survived: {s['text']}")
        for i in s["faq_ids"]:
            if i not in faq:
                problems.append(f"cites missing entry {i}")
    cited = {c["id"] for c in res["citations"]}
    for i in case.get("expect_cited", []):
        if i not in cited:
            problems.append(f"expected citation {i} not present")
    replaced = sum(1 for s in res["sentences"] if s.get("replaced"))
    if replaced != case.get("expect_replaced", 0):
        problems.append(f"{replaced} sentence(s) replaced, expected {case.get('expect_replaced', 0)}")
    if case.get("expect_confirm") and not any(s["type"] == "confirm" for s in res["sentences"]):
        problems.append("expected an \"I'll confirm\" sentence for the unanswered question")
    return problems


def run_case(case: dict) -> dict:
    try:
        if case["skill"] == "production-report":
            problems = check_narrative(case) if case.get("check") == "narrative" else check_numbers(case)
        elif case["skill"] == "quote-intake":
            problems = check_quote(case)
        else:
            problems = check_reply(case)
    except Exception as exc:  # a crash is a failed case, not a crashed run
        problems = [f"error: {exc}"]
    return {"id": case["id"], "skill": case["skill"], "title": case["title"], "passed": not problems,
            "problems": problems}


def run_all() -> dict:
    cases = json.loads(CASES.read_text())
    results = [run_case(c) for c in cases]
    passed = sum(r["passed"] for r in results)
    return {"results": results, "passed": passed, "total": len(results),
            "pass_rate": round(passed / len(results) * 100, 1) if results else 0.0,
            "mode": "demo" if config.demo_mode() else "real"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = run_all()
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Evals ({out['mode']} mode)\n")
        for r in out["results"]:
            print(f"  {'PASS' if r['passed'] else 'FAIL'}  {r['id']}  {r['title']}")
            for p in r["problems"]:
                print(f"          - {p}")
        print(f"\nPass rate: {out['passed']}/{out['total']} ({out['pass_rate']:.0f}%)")
    return 0 if out["passed"] == out["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
