"""The writer: Claude in real mode, recorded responses in demo mode.

Every call returns JSON matching a schema. The skills' scripts then check it:
numbers must be placeholders, quote fields must quote the email, reply facts must cite the FAQ.

Demo mode (DEMO_MODE=1) never touches the network. It replays fixtures/llm/<skill>/*.json.
If an input has no recording, it falls back to agency/offline.py and says so on screen.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache

from agency import config, offline


@dataclass
class WriterResult:
    data: dict
    source: str  # "claude", "recorded" or "rule-based"
    model: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return {
            "claude": f"Written by Claude ({self.model})",
            "recorded": "Demo mode: recorded response",
            "rule-based": "Demo mode: no recording for this input, showing a rule-based draft",
        }[self.source]


def input_key(text: str) -> str:
    """Stable key for a pasted email or message: whitespace and case do not matter."""
    return hashlib.sha256(" ".join(text.lower().split()).encode()).hexdigest()[:16]


# ---------------------------------------------------------------- prompts and schemas

NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "paragraphs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["headline", "paragraphs"],
    "additionalProperties": False,
}

BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "bullets": {"type": "array", "items": {"type": "string"}},
        "actions": {"type": "array", "items": {"type": "string"}},
        "email_subject": {"type": "string"},
        "email_body": {"type": "string"},
    },
    "required": ["headline", "bullets", "actions", "email_subject", "email_body"],
    "additionalProperties": False,
}

FIELD = {
    "type": "object",
    "properties": {"value": {"type": "string"}, "source": {"type": "string"}},
    "required": ["value", "source"],
    "additionalProperties": False,
}
QUOTE_KEYS = ["customer_name", "contact", "line_of_business", "effective_date", "zip_code", "drivers", "vehicles",
              "property_address", "year_built", "square_feet", "roof_age", "business_type", "annual_revenue",
              "employee_count", "years_in_business", "date_of_birth", "coverage_amount", "tobacco_use",
              "current_carrier", "current_premium"]
QUOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {"type": "object", "properties": {k: FIELD for k in QUOTE_KEYS}, "additionalProperties": False},
        "notes": {"type": "string"},
    },
    "required": ["fields", "notes"],
    "additionalProperties": False,
}

REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "greeting": {"type": "string"},
        "sentences": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "type": {"type": "string", "enum": ["fact", "courtesy", "confirm"]},
                "faq_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["text", "type", "faq_ids"],
            "additionalProperties": False,
        }},
        "sign_off": {"type": "string"},
    },
    "required": ["greeting", "sentences", "sign_off"],
    "additionalProperties": False,
}

NUMBERS_RULE = (
    "You must not type any digit. Refer to every number only through a placeholder from the metrics list, "
    "written exactly as {{key}}, for example {{total_premium}} or {{producer.grant_fowler.pct_of_target}}. "
    "Code fills in the values and deletes any sentence with a digit you typed."
)

NARRATIVE_SYSTEM = f"""You write the weekly production report narrative for {config.AGENCY_NAME}, an insurance agency.
Reader: the owner, who has two minutes. Plain words, no jargon, no em dashes, no emojis.
Write a one-line headline and exactly two short paragraphs: first the overall result, then the flags in plain words.
Explain only the flags you are given. Never invent a cause; if the reason is unknown, suggest the owner asks the producer.
If rows were skipped, say so. {NUMBERS_RULE}"""

BRIEF_SYSTEM = f"""You write the one-page weekly owner brief and a short email to the team for {config.AGENCY_NAME}.
Plain words, warm and direct, no em dashes, no emojis. Headline: one line, outcome first.
Bullets: exactly three (overall result, who stood out, what needs attention). Actions: up to three concrete next steps
for the owner, based only on the flags. Email: 4 to 7 sentences to the producers, encouraging, never singling anyone out
harshly. Never invent causes. {NUMBERS_RULE}"""

QUOTE_SYSTEM = """You turn a customer's quote request email into structured fields for an insurance producer.
For each field you find, return the value and the exact words from the email it came from ("source"), copied
character for character. Write dates and amounts exactly as the customer wrote them; never convert or compute them.
If a field is not in the email, leave it out entirely. Never guess. line_of_business lists every line asked for
(auto, home, commercial, life). contact is a phone number or email address. drivers lists each driver with their
date of birth if given. vehicles lists year, make and model. Put anything else useful in notes."""

REPLY_SYSTEM = f"""You draft replies to customer emails for {config.AGENCY_NAME}. Follow the tone guide.
You may only state facts that are in the FAQ. Split the reply body into sentences, each with a type:
- fact: anything about the agency, policies, prices, times or steps. Cite every FAQ id it relies on in faq_ids
  and say no more than those entries say.
- courtesy: thanks or greetings, no facts.
- confirm: for every question the FAQ does not answer, write a sentence that says you will confirm it with the team.
Never promise coverage, prices or claim outcomes. Greeting uses the customer's first name.
Sign off with "Best regards,\\nFernhill Insurance Agency"."""


# ---------------------------------------------------------------- fixtures


@lru_cache(maxsize=None)
def _fixtures(skill: str) -> dict:
    out = {}
    folder = config.FIXTURES_DIR / skill
    if folder.exists():
        for path in sorted(folder.glob("*.json")):
            item = json.loads(path.read_text())
            out[item["key"]] = item
    return out


def _replay(skill: str, key: str, check=None) -> dict | None:
    item = _fixtures(skill).get(key)
    if item and (check is None or check(item)):
        return item["response"]
    return None


# ---------------------------------------------------------------- real calls


def _call_claude(model: str, system: str, user: str, schema: dict) -> dict:
    if not config.api_key():
        raise RuntimeError("DEMO_MODE=0 needs ANTHROPIC_API_KEY. Set it in .env, or use DEMO_MODE=1.")
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined this request.")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def _report_payload(report: dict) -> str:
    """Only what the writer needs: computed metrics, flags and data issues. No customer rows."""
    return json.dumps({
        "week": report["week"],
        "metrics": report["metrics"],
        "flags": [{k: f[k] for k in ("id", "level", "title")} for f in report["flags"]],
        "data_issues": report["data_issues"],
    }, indent=1)


# ---------------------------------------------------------------- public API


def write_narrative(report: dict) -> WriterResult:
    if config.demo_mode():
        data = _replay("production-report", report["week"],
                       lambda item: item.get("total_premium") == report["totals"]["total_premium"])
        if data:
            return WriterResult(data, "recorded")
        return WriterResult(offline.narrative(report), "rule-based")
    data = _call_claude(config.WRITER_MODEL, NARRATIVE_SYSTEM, _report_payload(report), NARRATIVE_SCHEMA)
    return WriterResult(data, "claude", config.WRITER_MODEL)


def write_brief(report: dict) -> WriterResult:
    if config.demo_mode():
        data = _replay("weekly-owner-brief", report["week"],
                       lambda item: item.get("total_premium") == report["totals"]["total_premium"])
        if data:
            return WriterResult(data, "recorded")
        return WriterResult(offline.brief(report), "rule-based")
    data = _call_claude(config.WRITER_MODEL, BRIEF_SYSTEM, _report_payload(report), BRIEF_SCHEMA)
    return WriterResult(data, "claude", config.WRITER_MODEL)


def extract_quote(email: str) -> WriterResult:
    if config.demo_mode():
        data = _replay("quote-intake", input_key(email))
        if data:
            return WriterResult(data, "recorded")
        return WriterResult(offline.extract_quote(email), "rule-based")
    data = _call_claude(config.INTAKE_MODEL, QUOTE_SYSTEM, email, QUOTE_SCHEMA)
    return WriterResult(data, "claude", config.INTAKE_MODEL)


def draft_reply(message: str, faq_markdown: str, tone_guide: str, faq: dict) -> WriterResult:
    if config.demo_mode():
        data = _replay("customer-reply", input_key(message))
        if data:
            return WriterResult(data, "recorded")
        return WriterResult(offline.draft_reply(message, faq), "rule-based")
    user = f"<tone_guide>\n{tone_guide}\n</tone_guide>\n<faq>\n{faq_markdown}\n</faq>\n<customer_email>\n{message}\n</customer_email>"
    data = _call_claude(config.WRITER_MODEL, REPLY_SYSTEM, user, REPLY_SCHEMA)
    return WriterResult(data, "claude", config.WRITER_MODEL)
