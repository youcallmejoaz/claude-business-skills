"""Read-only queries over the agency's CSV and Excel exports.

These four functions are the whole connector. server.py exposes them over MCP;
Skills Studio's connector console calls the same functions. Nothing here writes,
deletes or sends: files are only ever opened for reading.
"""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

from agency import config, skill_runner

OPEN_STATUSES = {"Open", "Quoted"}


def _read_csv(name: str) -> list[dict]:
    with open(config.data_dir() / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _production_files() -> dict[str, Path]:
    files = sorted((config.data_dir() / "production").glob("production_*.xlsx"))
    return {p.stem.replace("production_", ""): p for p in files}


def list_reports() -> dict:
    """List the exports the connector can read: weekly production workbooks, customers and quotes."""
    weeks = _production_files()
    return {
        "production_weeks": [{"week": w, "file": p.name} for w, p in weeks.items()],
        "customers": {"file": "customers.csv", "rows": len(_read_csv("customers.csv"))},
        "quotes": {"file": "quotes.csv", "rows": len(_read_csv("quotes.csv"))},
        "as_of": config.as_of_date().isoformat(),
    }


def get_production(period: str = "latest", producer: str | None = None) -> dict:
    """Production numbers for one week ('2026-W43', or 'latest'), optionally for one producer."""
    weeks = _production_files()
    if not weeks:
        return {"error": "No production files found."}
    week = max(weeks) if period in (None, "", "latest") else period.strip().upper()
    if week not in weeks:
        return {"error": f"No production file for {period}.", "available": sorted(weeks)}
    rep = skill_runner.report()
    report = rep.compute(weeks[week])
    out = {"week": report["week"], "week_ending": report["week_ending"], "source": report["source"]}
    if producer:
        name = producer.strip().lower()
        rows = [p for p in report["by_producer"] if name in p["producer"].lower()]
        if not rows:
            return {**out, "error": f"No producer matching '{producer}'.",
                    "producers": [p["producer"] for p in report["by_producer"]]}
        data = rep.load(weeks[week])
        policies = [{"date": r["date"].isoformat() if r["date"] else None, "policy": r["policy"],
                     "line": r["line"], "type": r["type"], "premium": r["premium"]}
                    for r in data["production"] if r["producer"] == rows[0]["producer"]]
        return {**out, "producer": rows[0], "policies": policies}
    return {**out, "totals": report["totals"], "by_line": report["by_line"], "by_producer": report["by_producer"],
            "flags": [{k: f[k] for k in ("level", "title", "detail")} for f in report["flags"]]}


def find_customer(name: str) -> dict:
    """Find customers whose name contains the text given, with their quotes."""
    q = name.strip().lower()
    if len(q) < 2:
        return {"error": "Give at least two letters of the name."}
    customers = [c for c in _read_csv("customers.csv") if q in c["name"].lower()]
    quotes = _read_csv("quotes.csv")
    for c in customers:
        c["quotes"] = [{k: v for k, v in qt.items() if k not in ("customer_id", "customer_name")}
                       for qt in quotes if qt["customer_id"] == c["customer_id"]]
    return {"query": name, "matches": customers}


def open_quotes(older_than_days: int = 7) -> dict:
    """Quotes still open (status Open or Quoted) requested more than N days ago, oldest first."""
    today = config.as_of_date()
    rows = []
    for qt in _read_csv("quotes.csv"):
        if qt["status"] not in OPEN_STATUSES:
            continue
        age = (today - dt.date.fromisoformat(qt["requested_date"])).days
        if age > older_than_days:
            rows.append({**qt, "age_days": age})
    rows.sort(key=lambda r: -r["age_days"])
    return {"as_of": today.isoformat(), "older_than_days": older_than_days, "count": len(rows), "quotes": rows}
