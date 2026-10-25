"""Rule-based drafts for demo mode when an input has no recorded response.

These keep the app usable on any file or pasted text without an API key. They are
deliberately simple and are always labelled on screen. Their output goes through the
same checks as Claude's, so they cannot invent numbers, quote fields or FAQ facts either.
"""

from __future__ import annotations

import re

from agency import skill_runner

# ---------------------------------------------------------------- production report and owner brief


def _flag_sentences(report: dict) -> list[str]:
    out = []
    slug = skill_runner.report().slugify
    for f in report["flags"]:
        if f["id"].startswith("below_target_"):
            k = slug(f["producer"])
            out.append(f"{f['producer']} is at {{{{producer.{k}.pct_of_target}}}} of target, "
                       "the lowest on the team, so it is worth a check-in on their pipeline.")
        elif f["id"].startswith("ahead_target_"):
            k = slug(f["producer"])
            out.append(f"{f['producer']} finished well ahead at {{{{producer.{k}.pct_of_target}}}} of target.")
        elif f["id"] == "retention_low":
            out.append("Retention is under the agency's line at {{retention_rate}}, "
                       "with {{renewals_lost}} renewals lost out of {{renewals_due}} due.")
        elif f["id"] == "wow_drop":
            out.append("Premium is down {{wow_change_pct}} on last week.")
        elif f["id"] == "data_issues":
            out.append("Some rows in the file could not be used and were skipped, listed under data notes.")
    return out


def narrative(report: dict) -> dict:
    m = report["metrics"]
    first = ("The agency wrote {{policies_written}} policies this week, {{new_policies}} new and "
             "{{renewal_policies}} renewals, and kept {{retention_rate}} of renewals due.")
    if m.get("wow_direction") in ("up", "down"):
        first += " Premium is {{wow_direction}} {{wow_change_pct}} on last week."
    flags = _flag_sentences(report) or ["No producer is off track this week."]
    return {"headline": "{{total_premium}} written this week, {{pct_of_target}} of target",
            "paragraphs": [first, " ".join(flags)]}


def brief(report: dict) -> dict:
    slug = skill_runner.report().slugify
    actions = []
    for f in report["flags"]:
        if f["id"].startswith("below_target_"):
            actions.append(f"Meet with {f['producer']} this week to review their pipeline.")
        elif f["id"] == "retention_low":
            actions.append("Ask producers to review this week's lost renewals.")
        elif f["id"] == "data_issues":
            actions.append("Ask the office to fix the skipped rows in the export.")
    ahead = [f for f in report["flags"] if f["id"].startswith("ahead_target_")]
    stood_out = (f"{ahead[0]['producer']} stood out at {{{{producer.{slug(ahead[0]['producer'])}.pct_of_target}}}} "
                 "of target." if ahead else "{{top_producer}} led the team against target.")
    return {
        "headline": "{{pct_of_target}} of target this week, with {{total_premium}} written",
        "bullets": [
            "The agency wrote {{policies_written}} policies worth {{total_premium}}.",
            stood_out,
            "{{lowest_producer}} needs attention at the bottom of the table.",
        ],
        "actions": actions[:3] or ["No action needed this week."],
        "email_subject": "Weekly production: week ending {{week_ending}}",
        "email_body": ("Hi team,\n\nThis week we wrote {{total_premium}} across {{policies_written}} policies, "
                       "which is {{pct_of_target}} of our target. Retention was {{retention_rate}}. "
                       "Thanks for the work that went into this.\n\nBest regards,\nFernhill Insurance Agency"),
    }


# ---------------------------------------------------------------- quote intake

MAKES = ("Honda|Toyota|Ford|Subaru|Civic|Nissan|Mazda|Jeep|Hyundai|Kia|Chevrolet|Tesla|Volkswagen|"
         "Ram|BMW|Audi|Dodge|GMC")
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
DATE = rf"(?:{MONTH} \d{{1,2}}(?:st|nd|rd|th)?|\d{{1,2}}/\d{{1,2}}/\d{{2,4}}|ASAP|as soon as possible)"


def _lines(email: str) -> list[str]:
    return [re.sub(r"^\s*(>\s*)+", "", ln).strip() for ln in email.splitlines() if ln.strip()]


def _field(value: str, source: str) -> dict:
    return {"value": value.strip(), "source": source.strip()}


def extract_quote(email: str) -> dict:
    fields: dict = {}
    lines = _lines(email)
    body = "\n".join(lines)

    m = re.search(r"^Name:\s*(.+)$", body, re.M) or re.search(r"^From:\s*([^<\n]+?)\s*<", body, re.M)
    if m:
        fields["customer_name"] = _field(m.group(1), m.group(1))

    m = re.search(r"\(?555\)?[ -]?555-01\d\d", body)
    if m:
        fields["contact"] = _field(m.group(0), m.group(0))
    else:
        m = re.search(r"[\w.]+@example\.com", body)
        if m:
            fields["contact"] = _field(m.group(0), m.group(0))

    words = body.lower()
    found = []
    for line, keys in [("Auto", ["auto", "car ", "car,", "vehicle", "van"]), ("Home", ["home", "house", "condo"]),
                       ("Commercial", ["business", "general liability", "commercial"]), ("Life", ["life"])]:
        if any(k in words for k in keys):
            found.append(line)
    if found:
        src = next((ln for ln in lines if any(k in ln.lower() for k in
                    ["insurance", "quote", "interested", "need"])), lines[0])
        fields["line_of_business"] = _field(" and ".join(found), src)

    for ln in lines:
        low = ln.lower()
        if any(w in low for w in ("born", "dob", "birth")):
            continue
        if any(w in low for w in ("start", "renew", "closing", "begin", "effective", "in place", "expire", "lapse")):
            m = re.search(DATE, ln, re.I)
            if m:
                fields["effective_date"] = _field(m.group(0), ln)
                break

    m = re.search(r"(?<![\d$,(-])\b(30[0-9]{3})\b(?![\d,])", body)
    if m:
        line = next(ln for ln in lines if m.group(1) in ln)
        fields["zip_code"] = _field(m.group(1), line)

    driver_lines = [ln for ln in lines if re.search(r"\b(born|dob)\b", ln, re.I)]
    if driver_lines and "Auto" in found:
        fields["drivers"] = _field(driver_lines[0], driver_lines[0])
    if driver_lines and "Life" in found:
        m = re.search(r"\d{1,2}/\d{1,2}/\d{4}", driver_lines[0])
        if m:
            fields["date_of_birth"] = _field(m.group(0), driver_lines[0])

    vehicles = re.findall(rf"(?:19|20)\d{{2}} (?:{MAKES})(?: [A-Z0-9][\w-]*)?", body)
    if vehicles:
        line = next(ln for ln in lines if vehicles[0] in ln)
        fields["vehicles"] = _field(", ".join(v for v in vehicles if v in line), line)

    m = re.search(r"\b\d{1,4} [A-Z][a-z]+ (?:Lane|Street|Court|Road|Drive|Avenue|View)\b[^\n]*", body)
    if m:
        fields["property_address"] = _field(m.group(0).rstrip(".,"), m.group(0))
    for pat, key in [(r"(?:built(?: in)?:?|from) (\d{4})", "year_built"), (r"(\d{4}) build", "year_built"),
                     (r"([\d,]{3,6}) ?(?:sq\.? ?ft|square feet)", "square_feet"),
                     (r"(\d+) employees", "employee_count"),
                     (r"(\d+ years) in business|open (\d+ years)", "years_in_business")]:
        m = re.search(pat, body, re.I)
        if m and key not in fields:
            value = next(g for g in m.groups() if g)
            fields[key] = _field(value, m.group(0))
    m = re.search(r"roof[^.\n]*?(\d+ years old|replaced in \d{4}|\(\d{4}\)|is (?:about )?\d+ years old)", body, re.I)
    if m:
        fields["roof_age"] = _field(m.group(1), m.group(0))
    m = re.search(r"revenue[^$\n]*(\$[\d,.]+ ?[MK]?)", body, re.I)
    if m:
        fields["annual_revenue"] = _field(m.group(1), m.group(0))
    if "Life" in found:
        m = re.search(r"\$[\d,]+(?: million)?|\$1 million", body)
        if m:
            fields["coverage_amount"] = _field(m.group(0), m.group(0))
        m = re.search(r"non-smoker|don't smoke|neither of us smokes", body, re.I)
        if m:
            fields["tobacco_use"] = _field("No", m.group(0))
    m = re.search(r"pay(?:ing)? [^$\n]*?(\$[\d,]+(?:/yr| a year| per year)?)", body, re.I)
    if m:
        fields["current_premium"] = _field(m.group(1), m.group(0))
    return {"fields": fields, "notes": "Rule-based draft: a producer should read the email too."}


# ---------------------------------------------------------------- customer reply


def draft_reply(message: str, faq: dict) -> dict:
    check = skill_runner.reply()
    m = re.search(r"^From:\s*([A-Za-z]+)", message, re.M)
    name = m.group(1) if m else ""
    body = "\n".join(ln for ln in message.splitlines() if not re.match(r"^(From|Subject):", ln))
    questions = [q.strip() for q in re.split(r"(?<=[?.!])\s+", body) if q.strip().endswith("?")] or [body]
    sentences = [{"text": "Thanks for getting in touch.", "type": "courtesy", "faq_ids": []}]
    used = set()
    for q in questions:
        hits = check.search(q, faq, k=1, min_score=0.34)
        if hits and hits[0]["id"] not in used:
            entry = hits[0]
            used.add(entry["id"])
            for s in re.split(r"(?<=\.)\s+", entry["answer"])[:2]:
                sentences.append({"text": s, "type": "fact", "faq_ids": [entry["id"]]})
        elif not hits:
            sentences.append({"text": check.CONFIRM, "type": "confirm", "faq_ids": []})
    return {"greeting": f"Hi {name}," if name else "Hello,", "sentences": sentences,
            "sign_off": "Best regards,\nFernhill Insurance Agency"}
