"""Replace the demo fixtures with live Claude responses for every sample input.

Needs DEMO_MODE=0 and ANTHROPIC_API_KEY. Costs a few cents in total.
    make record-fixtures
Responses still go through the same checks in the app and the evals.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agency import config, llm, services  # noqa: E402


def save(skill: str, name: str, item: dict) -> None:
    path = config.FIXTURES_DIR / skill / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item, indent=2) + "\n")
    print(f"recorded {path.relative_to(ROOT)}")


def main() -> int:
    if config.demo_mode() or not config.api_key():
        print("Set DEMO_MODE=0 and ANTHROPIC_API_KEY to record live responses.")
        return 2
    for path in services.sample_weeks():
        report = services.compute(path)
        meta = {"key": report["week"], "total_premium": report["totals"]["total_premium"]}
        save("production-report", report["week"], {**meta, "response": llm.write_narrative(report).data})
        save("weekly-owner-brief", report["week"], {**meta, "response": llm.write_brief(report).data})
    for path in services.sample_emails():
        text = path.read_text()
        save("quote-intake", path.stem, {"key": llm.input_key(text), "input": str(path.relative_to(ROOT)),
                                         "response": llm.extract_quote(text).data})
    faq_md = (config.KNOWLEDGE_DIR / "faq.md").read_text()
    tone = (config.KNOWLEDGE_DIR / "tone-guide.md").read_text()
    for path in services.sample_messages():
        text = path.read_text()
        save("customer-reply", path.stem, {"key": llm.input_key(text), "input": str(path.relative_to(ROOT)),
                                           "response": llm.draft_reply(text, faq_md, tone, services.faq()).data})
    return 0


if __name__ == "__main__":
    sys.exit(main())
