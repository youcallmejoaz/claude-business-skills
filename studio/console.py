"""Data connector console: a question in, one read-only tool call out, shown as a table.

Real mode: Claude picks the tool and its arguments (tool use).
Demo mode: simple keyword matching picks it, so it works with no key.
Either way the tool is one of the four read-only functions in connector/tools.py,
the same ones the MCP server exposes to Claude Desktop.
"""

from __future__ import annotations

import json
import re

from agency import config
from connector import tools

EXAMPLES = [
    "Show open quotes older than 7 days",
    "How did Grant Fowler do this week?",
    "Find customer Lopez",
    "Which reports can you read?",
]

TOOL_DEFS = [
    {"name": "list_reports", "description": "List the exports available: weekly production workbooks, customers and quotes.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_production", "description": "Production numbers for one week ('2026-W43' or 'latest'), optionally for one producer.",
     "input_schema": {"type": "object", "properties": {"period": {"type": "string"}, "producer": {"type": "string"}},
                      "additionalProperties": False}},
    {"name": "find_customer", "description": "Find customers whose name contains the given text, with their quotes.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"],
                      "additionalProperties": False}},
    {"name": "open_quotes", "description": "Quotes still open (Open or Quoted) requested more than older_than_days ago.",
     "input_schema": {"type": "object", "properties": {"older_than_days": {"type": "integer"}},
                      "additionalProperties": False}},
]
FUNCS = {"list_reports": tools.list_reports, "get_production": tools.get_production,
         "find_customer": tools.find_customer, "open_quotes": tools.open_quotes}


def route_keywords(question: str) -> tuple[str, dict]:
    q = question.lower()
    if "quote" in q and any(w in q for w in ("open", "older", "old", "stale", "pending")):
        m = re.search(r"(\d+)\s*day", q)
        return "open_quotes", {"older_than_days": int(m.group(1)) if m else 7}
    m = re.search(r"(?:customer|find|look up|lookup)\s+(?:named\s+|called\s+)?([a-z][a-z' -]+)", q)
    if m and "production" not in q:
        return "find_customer", {"name": m.group(1).strip().rstrip("?. ")}
    if any(w in q for w in ("production", "premium", "how did", "target", "week", "producer")):
        args: dict = {"period": "latest"}
        w = re.search(r"\b(20\d\d)-?w(\d\d)\b", q)
        if w:
            args["period"] = f"{w.group(1)}-W{w.group(2)}"
        producers = [p["producer"] for p in tools.get_production("latest").get("by_producer", [])]
        for name in producers:
            if any(part.lower() in q for part in name.split()):
                args["producer"] = name
                break
        return "get_production", args
    return "list_reports", {}


def route_claude(question: str) -> tuple[str, dict]:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=config.INTAKE_MODEL,
        max_tokens=2000,
        system="You answer questions about an insurance agency's data by calling exactly one of the tools. "
               "Pick the single best tool and arguments.",
        tools=TOOL_DEFS,
        messages=[{"role": "user", "content": question}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name in FUNCS:
            return block.name, dict(block.input)
    return route_keywords(question)


def _table(result: dict) -> tuple[list[str], list[dict]]:
    for key in ("quotes", "matches", "policies", "by_producer", "production_weeks"):
        rows = result.get(key)
        if isinstance(rows, list) and rows:
            flat = [{k: v for k, v in r.items() if not isinstance(v, (list, dict)) and k != "customer_id"}
                    for r in rows]
            return list(flat[0].keys()), flat
    if "producer" in result and isinstance(result["producer"], dict):
        return list(result["producer"].keys()), [result["producer"]]
    return [], []


def ask(question: str) -> dict:
    if config.demo_mode() or not config.api_key():
        tool, args = route_keywords(question)
        chooser = "Demo mode: tool picked by keyword matching"
    else:
        tool, args = route_claude(question)
        chooser = f"Tool picked by Claude ({config.INTAKE_MODEL})"
    result = FUNCS[tool](**args)
    columns, rows = _table(result)
    summary = {k: v for k, v in result.items() if not isinstance(v, (list, dict))}
    return {"question": question, "tool": tool, "args": args, "call": f"{tool}({json.dumps(args)})",
            "chooser": chooser, "columns": columns, "rows": rows, "summary": summary,
            "extra": result.get("producer") if "policies" in result else None}
