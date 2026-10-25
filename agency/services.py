"""One function per skill: run the skill's script, ask the writer, check the result.

Used by Skills Studio and the evals so both run exactly the same path.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from agency import config, llm, skill_runner


# ---------------------------------------------------------------- production report and owner brief


def sample_weeks() -> list[Path]:
    return sorted((config.data_dir() / "production").glob("production_*.xlsx"))


def previous_week_file(week: str) -> Path | None:
    try:
        year, num = week.split("-W")
        monday = dt.date.fromisocalendar(int(year), int(num), 1)
    except ValueError:
        return None
    y, w, _ = (monday - dt.timedelta(days=7)).isocalendar()
    candidate = config.data_dir() / "production" / f"production_{y}-W{w:02d}.xlsx"
    return candidate if candidate.exists() else None


def compute(path: Path) -> dict:
    compute_report = skill_runner.report().compute
    first = compute_report(path)
    prev = previous_week_file(first["week"])
    if prev and prev.resolve() != Path(path).resolve():
        return compute_report(path, prev)
    return first


def run_report(path: Path) -> dict:
    report = compute(path)
    writer = llm.write_narrative(report)
    fill = skill_runner.narrative().fill
    problems = []
    headline, p = fill(writer.data.get("headline", ""), report["metrics"])
    problems += p
    paragraphs = []
    for para in writer.data.get("paragraphs", []):
        text, p = fill(para, report["metrics"])
        problems += p
        if text:
            paragraphs.append(text)
    return {"report": report, "headline": headline, "paragraphs": paragraphs, "problems": problems,
            "writer": writer}


def run_brief(path: Path) -> dict:
    report = compute(path)
    writer = llm.write_brief(report)
    build = skill_runner.brief()
    brief, problems = build.fill_brief(writer.data, report["metrics"])
    html_text = build.render_html(report, brief, config.AGENCY_NAME)
    return {"report": report, "brief": brief, "problems": problems, "html": html_text, "writer": writer}


# ---------------------------------------------------------------- quote intake


def sample_emails() -> list[Path]:
    return sorted((config.data_dir() / "quote_emails").glob("*.txt"))


def run_intake(email: str) -> dict:
    writer = llm.extract_quote(email)
    result = skill_runner.quote().check(email, writer.data)
    return {"email": email, "extraction": writer.data, "result": result, "writer": writer}


# ---------------------------------------------------------------- customer reply


def sample_messages() -> list[Path]:
    return sorted((config.data_dir() / "customer_messages").glob("*.txt"))


def faq() -> dict:
    return skill_runner.reply().parse_faq(config.KNOWLEDGE_DIR / "faq.md")


def run_reply(message: str) -> dict:
    entries = faq()
    writer = llm.draft_reply(message, (config.KNOWLEDGE_DIR / "faq.md").read_text(),
                             (config.KNOWLEDGE_DIR / "tone-guide.md").read_text(), entries)
    result = skill_runner.reply().check(writer.data, entries)
    return {"message": message, "draft": writer.data, "result": result, "writer": writer}
