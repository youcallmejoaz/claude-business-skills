"""Quote intake never invents a value and always lists what is missing."""

import json
from pathlib import Path

from agency import config, llm, offline, skill_runner

check = skill_runner.quote().check
EMAIL = "From: Ana Test <ana@example.com>\nI need a car quote. 2018 Toyota Corolla. Start on Nov 14. ZIP 30801."


def f(value, source):
    return {"value": value, "source": source}


def test_valid_fields_are_kept_and_missing_listed():
    res = check(EMAIL, {"fields": {
        "customer_name": f("Ana Test", "From: Ana Test"),
        "line_of_business": f("Auto", "I need a car quote"),
        "effective_date": f("Nov 14", "Start on Nov 14"),
        "zip_code": f("30801", "ZIP 30801"),
        "vehicles": f("2018 Toyota Corolla", "2018 Toyota Corolla"),
    }})
    assert res["lines"] == ["Auto"]
    assert [m["key"] for m in res["missing"]] == ["contact", "drivers"]
    assert res["rejected"] == []
    assert all(m["question"] for m in res["missing"])


def test_invented_date_is_rejected():
    res = check(EMAIL, {"fields": {"effective_date": f("Nov 15", "Start on Nov 14")}})
    assert res["rejected"][0]["key"] == "effective_date"
    assert "effective_date" in [m["key"] for m in res["missing"]]


def test_converted_date_is_rejected():
    # "Nov 14" written as 2026-11-14 adds a year the customer never gave.
    res = check(EMAIL, {"fields": {"effective_date": f("2026-11-14", "Start on Nov 14")}})
    assert res["rejected"] and res["rejected"][0]["key"] == "effective_date"


def test_invented_amount_and_fake_source_are_rejected():
    res = check(EMAIL, {"fields": {
        "current_premium": f("$1,200 a year", "I pay $1,200 a year"),
        "annual_revenue": f("$50,000", "ZIP 30801"),
    }})
    reasons = {r["key"]: r["reason"] for r in res["rejected"]}
    assert "not in the email" in reasons["current_premium"]
    assert "number" in reasons["annual_revenue"]


def test_month_change_is_rejected():
    res = check(EMAIL, {"fields": {"effective_date": f("Dec 14", "Start on Nov 14")}})
    assert res["rejected"]


def test_bundle_needs_both_lines():
    res = check(EMAIL, {"fields": {"line_of_business": f("Auto and Home", "I need a car quote")}})
    keys = [m["key"] for m in res["missing"]]
    assert "vehicles" in keys and "roof_age" in keys


def test_commercial_property_is_not_a_home_quote():
    res = check("We need general liability and commercial property for the shop.",
                {"fields": {"line_of_business": f("Commercial: general liability and commercial property",
                                                  "We need general liability and commercial property")}})
    assert res["lines"] == ["Commercial"]


def test_forwarded_quote_markers_are_ignored():
    email = "Fwd:\n> We're Rise & Shine Bakery,\n> 7 Mill Road"
    res = check(email, {"fields": {"business_type": f("Bakery", "We're Rise & Shine Bakery, 7 Mill Road")}})
    assert res["rejected"] == []


def test_every_recorded_fixture_passes_the_source_check():
    folder = config.FIXTURES_DIR / "quote-intake"
    files = sorted(folder.glob("*.json"))
    assert len(files) == 25
    for path in files:
        item = json.loads(path.read_text())
        email = (config.ROOT / item["input"]).read_text()
        assert item["key"] == llm.input_key(email), path.name
        assert check(email, item["response"])["rejected"] == [], path.name


def test_rule_based_parser_never_invents():
    for path in sorted((config.data_dir() / "quote_emails").glob("*.txt")):
        email = path.read_text()
        assert check(email, offline.extract_quote(email))["rejected"] == [], path.name


def test_checklist_matches_project_knowledge():
    skill_copy = config.SKILLS_DIR / "quote-intake" / "reference" / "quote-checklist.md"
    assert skill_copy.read_text() == (config.KNOWLEDGE_DIR / "quote-checklist.md").read_text()
    keys = [r["key"] for r in skill_runner.quote().load_checklist()]
    assert len(keys) == 18 and keys[0] == "customer_name"
