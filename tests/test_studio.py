"""Skills Studio works end to end in demo mode, with no API key."""

import re

import pytest
from fastapi.testclient import TestClient

from agency import config, pdf
from studio.app import app

client = TestClient(app)


@pytest.mark.parametrize("url", ["/", "/skills/production-report", "/skills/weekly-owner-brief",
                                 "/skills/quote-intake", "/skills/customer-reply", "/evals", "/connector"])
def test_pages_load(url):
    r = client.get(url)
    assert r.status_code == 200
    assert "Demo mode" in r.text


def test_production_report_from_sample_and_upload():
    r = client.post("/run/production-report", data={"sample": "production_2026-W43.xlsx"})
    assert r.status_code == 200
    assert "Grant Fowler is below target" in r.text and "Calculated by script" in r.text
    assert "{{" not in r.text
    with open(config.data_dir() / "production" / "production_2026-W40.xlsx", "rb") as f:
        r = client.post("/run/production-report", files={"file": ("week.xlsx", f)}, data={"sample": ""})
    assert "1 skipped" in r.text


def test_owner_brief_pdf_is_one_page():
    r = client.post("/run/weekly-owner-brief", data={"sample": "production_2026-W43.xlsx"})
    assert "data:image/png;base64" in r.text
    token = re.search(r"/export/brief/([^\"]+)", r.text).group(1)
    p = client.get(f"/export/brief/{token}")
    assert p.headers["content-type"] == "application/pdf"
    assert p.content.startswith(b"%PDF") and pdf.page_count(p.content) == 1


def test_quote_intake_and_reply():
    email = (config.data_dir() / "quote_emails" / "q01_bundle_auto_home.txt").read_text()
    r = client.post("/run/quote-intake", data={"email": email})
    assert "Missing information" in r.text and "How old is the roof?" in r.text
    msg = (config.data_dir() / "customer_messages" / "m09_roadside.txt").read_text()
    r = client.post("/run/customer-reply", data={"message": msg})
    assert "FAQ-16" in r.text and "Replaced an unsupported sentence" in r.text


def test_empty_input_is_handled():
    assert "Paste a quote request" in client.post("/run/quote-intake", data={"email": " "}).text
    assert "Choose a sample week" in client.post("/run/production-report", data={"sample": ""}).text


def test_evals_and_connector():
    assert "12 / 12" in client.post("/evals/run").text
    r = client.post("/connector/ask", data={"question": "show open quotes older than 7 days"})
    assert "open_quotes" in r.text and "Read-only" in r.text


def test_nothing_is_sent():
    # No route in the app can send email or post anywhere.
    paths = {route.path for route in app.routes}
    assert not any(word in p for p in paths for word in ("send", "email", "mail"))
