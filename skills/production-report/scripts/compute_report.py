"""Compute the weekly production report numbers from the producers' Excel export.

Every number in the report comes from this script. Claude only writes the explanation.

Usage:
    python compute_report.py production_2026-W43.xlsx [--previous production_2026-W42.xlsx] [--json]

Expected workbook (column names are matched without regard to case or spacing):
    Production    Date, Producer, Policy Number, Customer, Line, Business Type, Written Premium
    Renewals Due  Producer, Policy Number, Line, Expiring Premium, Outcome
    Targets       Producer, Weekly Premium Target

Cleans the usual export noise: title rows above the header, blank rows, a TOTAL row,
premiums stored as text like "$1,250.00", and names in odd case or with extra spaces.
Rows it cannot use are skipped and listed under data issues, never guessed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

LINES = ["Auto", "Home", "Commercial", "Life"]
BELOW_TARGET_PCT = 80.0
AHEAD_TARGET_PCT = 120.0
RETENTION_WATCH_PCT = 85.0
WOW_DROP_PCT = -10.0

PRODUCTION_COLS = {
    "date": "date", "producer": "producer", "policynumber": "policy", "customer": "customer",
    "line": "line", "lineofbusiness": "line", "businesstype": "type", "newrenewal": "type",
    "writtenpremium": "premium", "premium": "premium",
}
RENEWAL_COLS = {"producer": "producer", "policynumber": "policy", "line": "line",
                "expiringpremium": "expiring", "outcome": "outcome"}
TARGET_COLS = {"producer": "producer", "weeklypremiumtarget": "target", "target": "target"}


def _key(text) -> str:
    return re.sub(r"[^a-z]", "", str(text).lower())


def _read_sheet(path: Path, sheet: str, colmap: dict, required: set) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    header_row = None
    for i in range(min(len(raw), 15)):
        keys = {colmap.get(_key(v)) for v in raw.iloc[i].tolist() if pd.notna(v)}
        if required <= keys:
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"Sheet '{sheet}': could not find a header row with {sorted(required)}")
    cols = [colmap.get(_key(v), f"_extra{j}") if pd.notna(v) else f"_extra{j}"
            for j, v in enumerate(raw.iloc[header_row].tolist())]
    df = raw.iloc[header_row + 1:].copy()
    df.columns = cols
    df["_row"] = [header_row + 2 + k for k in range(len(df))]  # 1-based Excel row number
    return df[[c for c in df.columns if not c.startswith("_extra")]]


def parse_money(value):
    """Return a float for 1250, 1250.5, '$1,250.50' or ' 1250 '. None if blank or unreadable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _clean_name(value, known: dict) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = " ".join(str(value).split())
    if not text:
        return None
    return known.get(text.lower(), text.title())


def _norm_choice(value, choices: list[str]) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    k = _key(value)
    for c in choices:
        if _key(c) == k:
            return c
    return None


def load(path: str | Path) -> dict:
    """Read and clean the workbook. Returns clean rows plus a list of data issues."""
    path = Path(path)
    issues: list[str] = []

    targets_df = _read_sheet(path, "Targets", TARGET_COLS, {"producer", "target"})
    targets = {}
    for _, r in targets_df.iterrows():
        name = _clean_name(r["producer"], {})
        t = parse_money(r["target"])
        if name and t is not None:
            targets[name] = t
    known = {n.lower(): n for n in targets}

    prod_df = _read_sheet(path, "Production", PRODUCTION_COLS, {"producer", "policy", "line", "type", "premium"})
    production = []
    for _, r in prod_df.iterrows():
        values = [r.get(c) for c in ("producer", "policy", "line", "type", "premium")]
        if all(v is None or (isinstance(v, float) and pd.isna(v)) for v in values):
            continue  # blank row
        producer = _clean_name(r["producer"], known)
        if producer and producer.lower() in {"total", "totals", "grand total"}:
            continue  # the export's own total row; we recompute totals ourselves
        policy = str(r["policy"]).strip() if pd.notna(r["policy"]) else ""
        premium = parse_money(r["premium"])
        line = _norm_choice(r["line"], LINES)
        btype = _norm_choice(r["type"], ["New", "Renewal"])
        problem = None
        if not producer:
            problem = "no producer"
        elif premium is None:
            problem = "no written premium"
        elif line is None:
            problem = f"unknown line '{r['line']}'"
        elif btype is None:
            problem = f"unknown business type '{r['type']}'"
        if problem:
            issues.append(f"Row {r['_row']} skipped ({problem}), policy {policy or 'blank'}")
            continue
        date = r.get("date")
        if isinstance(date, (pd.Timestamp, dt.datetime)):
            date = date.date()
        production.append({"row": int(r["_row"]), "date": date if isinstance(date, dt.date) else None,
                           "producer": producer, "policy": policy, "line": line, "type": btype,
                           "premium": premium})

    ren_df = _read_sheet(path, "Renewals Due", RENEWAL_COLS, {"producer", "policy", "outcome"})
    renewals = []
    for _, r in ren_df.iterrows():
        producer = _clean_name(r["producer"], known)
        outcome = _norm_choice(r["outcome"], ["Renewed", "Lost"])
        if not producer and outcome is None:
            continue
        if outcome is None:
            issues.append(f"Renewals Due row {r['_row']} skipped (unknown outcome '{r['outcome']}')")
            continue
        renewals.append({"producer": producer, "policy": str(r["policy"]).strip(), "outcome": outcome,
                         "line": _norm_choice(r.get("line"), LINES),
                         "expiring": parse_money(r.get("expiring"))})

    for p in sorted({row["producer"] for row in production} - set(targets)):
        issues.append(f"Producer '{p}' has no weekly target; shown without a target")

    return {"production": production, "renewals": renewals, "targets": targets, "issues": issues,
            "file": path.name}


def _week_label(production: list[dict]) -> tuple[str, str | None]:
    dates = [r["date"] for r in production if r["date"]]
    if not dates:
        return "unknown week", None
    (year, week), _ = Counter(d.isocalendar()[:2] for d in dates).most_common(1)[0]
    friday = dt.date.fromisocalendar(year, week, 5)
    return f"{year}-W{week:02d}", friday.isoformat()


def _pct(part: float, whole: float) -> float | None:
    return round(part / whole * 100, 1) if whole else None


def compute(path: str | Path, previous: str | Path | None = None) -> dict:
    data = load(path)
    prod, ren, targets = data["production"], data["renewals"], data["targets"]
    week, week_ending = _week_label(prod)

    total = round(sum(r["premium"] for r in prod), 2)
    target_total = round(sum(targets.values()), 2)
    renewed = sum(1 for r in ren if r["outcome"] == "Renewed")

    by_line = []
    for line in LINES:
        rows = [r for r in prod if r["line"] == line]
        by_line.append({
            "line": line,
            "policies": len(rows),
            "new": sum(1 for r in rows if r["type"] == "New"),
            "renewal": sum(1 for r in rows if r["type"] == "Renewal"),
            "premium": round(sum(r["premium"] for r in rows), 2),
        })

    producers = list(targets) + sorted({r["producer"] for r in prod} - set(targets))
    by_producer = []
    for name in producers:
        rows = [r for r in prod if r["producer"] == name]
        prem = round(sum(r["premium"] for r in rows), 2)
        due = [r for r in ren if r["producer"] == name]
        kept = sum(1 for r in due if r["outcome"] == "Renewed")
        target = targets.get(name)
        by_producer.append({
            "producer": name,
            "policies": len(rows),
            "new": sum(1 for r in rows if r["type"] == "New"),
            "renewal": sum(1 for r in rows if r["type"] == "Renewal"),
            "premium": prem,
            "target": target,
            "pct_of_target": _pct(prem, target) if target else None,
            "renewals_due": len(due),
            "renewals_kept": kept,
            "retention_rate": _pct(kept, len(due)),
        })

    totals = {
        "total_premium": total,
        "policies_written": len(prod),
        "new_policies": sum(1 for r in prod if r["type"] == "New"),
        "renewal_policies": sum(1 for r in prod if r["type"] == "Renewal"),
        "new_premium": round(sum(r["premium"] for r in prod if r["type"] == "New"), 2),
        "renewal_premium": round(sum(r["premium"] for r in prod if r["type"] == "Renewal"), 2),
        "renewals_due": len(ren),
        "renewals_kept": renewed,
        "renewals_lost": len(ren) - renewed,
        "retention_rate": _pct(renewed, len(ren)),
        "target_total": target_total,
        "pct_of_target": _pct(total, target_total),
    }

    prior = None
    if previous:
        prev = compute(previous)
        prior = {"week": prev["week"], "total_premium": prev["totals"]["total_premium"],
                 "policies_written": prev["totals"]["policies_written"]}
        totals["prior_total_premium"] = prior["total_premium"]
        totals["wow_change_pct"] = _pct(total - prior["total_premium"], prior["total_premium"])

    report = {
        "week": week,
        "week_ending": week_ending,
        "source": {"file": data["file"], "rows_used": len(prod), "renewal_rows": len(ren),
                   "rows_skipped": sum(1 for i in data["issues"] if "skipped" in i)},
        "totals": totals,
        "by_line": by_line,
        "by_producer": by_producer,
        "prior_week": prior,
        "data_issues": data["issues"],
    }
    report["flags"] = build_flags(report)
    report["metrics"] = metric_values(report)
    return report


def _whole(v: float) -> int:
    """Round half up (114.5 -> 115), the way people round by hand, not banker's rounding."""
    return int(Decimal(str(v)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def money(v: float | None) -> str:
    return "n/a" if v is None else f"${_whole(v):,}"


def pct(v: float | None) -> str:
    return "n/a" if v is None else f"{_whole(v)}%"


def build_flags(report: dict) -> list[dict]:
    """Rule-based flags. The thresholds are the agency's, set at the top of this file."""
    flags = []
    t = report["totals"]
    for p in report["by_producer"]:
        slug = slugify(p["producer"])
        if p["pct_of_target"] is not None and p["pct_of_target"] < BELOW_TARGET_PCT:
            flags.append({"id": f"below_target_{slug}", "level": "red",
                          "title": f"{p['producer']} is below target",
                          "detail": f"{money(p['premium'])} written against a {money(p['target'])} target "
                                    f"({pct(p['pct_of_target'])}).",
                          "producer": p["producer"]})
        elif p["pct_of_target"] is not None and p["pct_of_target"] >= AHEAD_TARGET_PCT:
            flags.append({"id": f"ahead_target_{slug}", "level": "green",
                          "title": f"{p['producer']} is well ahead of target",
                          "detail": f"{money(p['premium'])} written against a {money(p['target'])} target "
                                    f"({pct(p['pct_of_target'])}).",
                          "producer": p["producer"]})
    if t["retention_rate"] is not None and t["retention_rate"] < RETENTION_WATCH_PCT:
        flags.append({"id": "retention_low", "level": "amber", "title": "Retention is below the 85% line",
                      "detail": f"{t['renewals_kept']} of {t['renewals_due']} renewals kept "
                                f"({pct(t['retention_rate'])})."})
    for p in report["by_producer"]:
        if p["renewals_due"] >= 2 and p["retention_rate"] is not None and p["retention_rate"] < 70:
            flags.append({"id": f"retention_{slugify(p['producer'])}", "level": "amber",
                          "title": f"{p['producer']} lost several renewals",
                          "detail": f"{p['renewals_kept']} of {p['renewals_due']} renewals kept.",
                          "producer": p["producer"]})
    if t.get("wow_change_pct") is not None and t["wow_change_pct"] <= WOW_DROP_PCT:
        flags.append({"id": "wow_drop", "level": "amber", "title": "Premium is down on last week",
                      "detail": f"{money(t['total_premium'])} this week against "
                                f"{money(t['prior_total_premium'])} last week ({pct(t['wow_change_pct'])})."})
    if report["data_issues"]:
        flags.append({"id": "data_issues", "level": "amber", "title": "Some rows could not be used",
                      "detail": "; ".join(report["data_issues"])})
    return flags


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def metric_values(report: dict) -> dict:
    """Flat {placeholder: display text}. The narrative may only use numbers through these."""
    t = report["totals"]
    m = {
        "week": report["week"],
        "week_ending": report["week_ending"] or "n/a",
        "total_premium": money(t["total_premium"]),
        "policies_written": str(t["policies_written"]),
        "new_policies": str(t["new_policies"]),
        "renewal_policies": str(t["renewal_policies"]),
        "new_premium": money(t["new_premium"]),
        "renewal_premium": money(t["renewal_premium"]),
        "renewals_due": str(t["renewals_due"]),
        "renewals_kept": str(t["renewals_kept"]),
        "renewals_lost": str(t["renewals_lost"]),
        "retention_rate": pct(t["retention_rate"]),
        "target_total": money(t["target_total"]),
        "pct_of_target": pct(t["pct_of_target"]),
    }
    if t.get("wow_change_pct") is not None:
        change = t["wow_change_pct"]
        m["prior_total_premium"] = money(t["prior_total_premium"])
        m["wow_change_pct"] = pct(abs(change))
        m["wow_direction"] = "up" if change > 0.5 else "down" if change < -0.5 else "flat"
    for row in report["by_line"]:
        k = row["line"].lower()
        m[f"line.{k}.policies"] = str(row["policies"])
        m[f"line.{k}.premium"] = money(row["premium"])
    ranked = sorted([p for p in report["by_producer"] if p["pct_of_target"] is not None],
                    key=lambda p: p["pct_of_target"], reverse=True)
    if ranked:
        m["top_producer"] = ranked[0]["producer"]
        m["lowest_producer"] = ranked[-1]["producer"]
    for p in report["by_producer"]:
        k = slugify(p["producer"])
        m[f"producer.{k}.premium"] = money(p["premium"])
        m[f"producer.{k}.policies"] = str(p["policies"])
        m[f"producer.{k}.target"] = money(p["target"])
        m[f"producer.{k}.pct_of_target"] = pct(p["pct_of_target"])
        m[f"producer.{k}.retention_rate"] = pct(p["retention_rate"])
    return m


def to_markdown(report: dict) -> str:
    t = report["totals"]
    out = [f"# Production report {report['week']} (week ending {report['week_ending']})", "",
           f"Source: {report['source']['file']}, {report['source']['rows_used']} rows used, "
           f"{report['source']['rows_skipped']} skipped.", "",
           "| Measure | Value |", "|---|---|",
           f"| Premium written | {money(t['total_premium'])} |",
           f"| Policies written | {t['policies_written']} ({t['new_policies']} new, {t['renewal_policies']} renewal) |",
           f"| Retention | {pct(t['retention_rate'])} ({t['renewals_kept']} of {t['renewals_due']}) |",
           f"| Agency vs target | {pct(t['pct_of_target'])} of {money(t['target_total'])} |"]
    if t.get("wow_change_pct") is not None:
        out.append(f"| Change vs last week | {t['wow_change_pct']:+.1f}% |")
    out += ["", "| Line | Policies | New | Renewal | Premium |", "|---|---|---|---|---|"]
    out += [f"| {r['line']} | {r['policies']} | {r['new']} | {r['renewal']} | {money(r['premium'])} |"
            for r in report["by_line"]]
    out += ["", "| Producer | Policies | Premium | Target | % of target | Retention |", "|---|---|---|---|---|---|"]
    out += [f"| {p['producer']} | {p['policies']} | {money(p['premium'])} | {money(p['target'])} | "
            f"{pct(p['pct_of_target'])} | {pct(p['retention_rate'])} |" for p in report["by_producer"]]
    if report["flags"]:
        out += ["", "## Flags"] + [f"- [{f['level']}] {f['title']}: {f['detail']}" for f in report["flags"]]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("workbook")
    ap.add_argument("--previous", help="last week's workbook, for the week-on-week change")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args(argv)
    report = compute(args.workbook, args.previous)
    print(json.dumps(report, indent=2, default=str) if args.json else to_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
