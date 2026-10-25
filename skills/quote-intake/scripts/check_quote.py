"""Check a structured quote request against the email it came from, and list what is missing.

Claude (or a person) extracts fields from the customer's email. Each field must carry
the exact text it came from. This script:
  1. rejects a field whose source text is not in the email,
  2. rejects a field whose value has a number or month that is not in its source text
     (so a date or amount can never be invented or "tidied up"),
  3. works out which fields are required from the lines asked for, using the agency's
     quote checklist, and lists every missing one with the question to ask the customer.

Usage:
    python check_quote.py email.txt extraction.json

extraction.json looks like:
    {"fields": {"customer_name": {"value": "Maria Lopez", "source": "Thanks, Maria Lopez"}, ...},
     "notes": "anything useful that is not a field"}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKLIST = HERE.parent / "reference" / "quote-checklist.md"

LINE_WORDS = {
    "Auto": ["auto", "car", "vehicle", "truck", "suv", "van", "driver"],
    "Home": ["home", "house", "homeowner", "property", "condo", "dwelling"],
    "Commercial": ["commercial", "business", "liability", "workers", "shop", "bakery", "company"],
    "Life": ["life", "term", "whole life"],
}
OPTIONAL = ["current_carrier", "current_premium", "notes"]
LABELS = {
    "customer_name": "Customer name", "contact": "Phone or email", "line_of_business": "Insurance wanted",
    "effective_date": "Start date", "zip_code": "ZIP code", "drivers": "Drivers", "vehicles": "Vehicles",
    "property_address": "Property address", "year_built": "Year built", "square_feet": "Square feet",
    "roof_age": "Roof age", "business_type": "Business type", "annual_revenue": "Annual revenue",
    "employee_count": "Employees", "years_in_business": "Years in business", "date_of_birth": "Date of birth",
    "coverage_amount": "Coverage amount", "tobacco_use": "Tobacco use", "current_carrier": "Current carrier",
    "current_premium": "Current premium", "notes": "Notes",
}
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep",
          "sept", "oct", "nov", "dec"]


def load_checklist(path: Path = CHECKLIST) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and re.fullmatch(r"[a-z_]+", cells[0]):
            rows.append({"key": cells[0], "for": cells[1].lower(), "question": cells[2]})
    return rows


def normalize(text: str) -> str:
    """Lowercase, drop forwarded-mail quote markers, unify quotes and collapse whitespace."""
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = "\n".join(re.sub(r"^\s*(>\s*)+", "", ln) for ln in text.splitlines())
    return " ".join(text.lower().split())


def numbers_in(text: str) -> list[str]:
    """Digit groups, with thousands separators removed: '$1,250.00' -> ['1250', '00']."""
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return re.findall(r"\d+", text)


def months_in(text: str) -> set[str]:
    words = set(re.findall(r"[a-z]+", text.lower()))
    return {m[:3] for m in MONTHS if m in words}


def lines_requested(value: str | None) -> list[str]:
    if not value:
        return []
    words = value.lower()
    return [line for line, keys in LINE_WORDS.items() if any(re.search(rf"\b{k}", words) for k in keys)]


def check(email: str, extraction: dict, checklist: list[dict] | None = None) -> dict:
    checklist = checklist or load_checklist()
    email_n = normalize(email)
    fields_in = extraction.get("fields", {})
    fields, rejected = {}, []

    for key, item in fields_in.items():
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        source = item.get("source") or ""
        if value in (None, "", []):
            continue
        value = str(value).strip()
        reason = None
        if key == "notes":
            fields[key] = {"value": value, "source": source, "label": LABELS.get(key, key)}
            continue
        if not source.strip():
            reason = "no source text given"
        elif normalize(source) not in email_n:
            reason = "source text is not in the email"
        else:
            src_numbers = numbers_in(normalize(source))
            missing_nums = [n for n in numbers_in(value) if n not in src_numbers]
            missing_months = months_in(value) - months_in(source)
            if missing_nums:
                reason = f"value has number(s) {missing_nums} that are not in the source text"
            elif missing_months:
                reason = "value has a month that is not in the source text"
        if reason:
            rejected.append({"key": key, "label": LABELS.get(key, key), "value": value, "reason": reason})
        else:
            fields[key] = {"value": value, "source": source, "label": LABELS.get(key, key)}

    lines = lines_requested(fields.get("line_of_business", {}).get("value"))
    needed = [row for row in checklist
              if row["for"] == "all" or any(row["for"] == ln.lower() for ln in lines)]
    rejected_keys = {r["key"] for r in rejected}
    missing = [{"key": row["key"], "label": LABELS.get(row["key"], row["key"]), "question": row["question"],
                "reason": "could not be verified in the email" if row["key"] in rejected_keys else "not in the email"}
               for row in needed if row["key"] not in fields]
    order = [row["key"] for row in needed] + [k for k in OPTIONAL if k in fields]
    ordered = [{"key": k, **fields[k]} for k in order if k in fields]
    return {
        "lines": lines,
        "fields": ordered,
        "missing": missing,
        "rejected": rejected,
        "required_count": len(needed),
        "complete": not missing,
        "questions_for_customer": [m["question"] for m in missing],
    }


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    email = Path(argv[0]).read_text()
    extraction = json.loads(Path(argv[1]).read_text())
    print(json.dumps(check(email, extraction), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
