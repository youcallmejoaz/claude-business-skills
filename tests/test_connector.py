"""The MCP connector returns the right rows and cannot change anything."""

import asyncio
import csv
import datetime as dt
import hashlib
import json

from agency import config, skill_runner
from connector import tools
from connector.server import server


def _hashes():
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(config.data_dir().rglob("*")) if p.is_file()}


def test_exactly_four_tools_all_read_only():
    listed = asyncio.run(server.list_tools())
    assert sorted(t.name for t in listed) == ["find_customer", "get_production", "list_reports", "open_quotes"]
    for t in listed:
        assert t.annotations.read_only_hint is True
        assert t.annotations.destructive_hint is False
        assert t.annotations.open_world_hint is False


def test_tools_leave_data_files_unchanged():
    before = _hashes()

    async def call_all():
        await server.call_tool("list_reports", {})
        await server.call_tool("get_production", {"period": "latest"})
        await server.call_tool("get_production", {"period": "2026-W40", "producer": "grant"})
        await server.call_tool("find_customer", {"name": "lopez"})
        await server.call_tool("open_quotes", {"older_than_days": 7})

    asyncio.run(call_all())
    assert _hashes() == before


def test_open_quotes_rows():
    with open(config.data_dir() / "quotes.csv") as f:
        rows = list(csv.DictReader(f))
    today = dt.date(2026, 10, 23)
    expected = sorted(r["quote_id"] for r in rows if r["status"] in ("Open", "Quoted")
                      and (today - dt.date.fromisoformat(r["requested_date"])).days > 7)
    got = tools.open_quotes(7)
    assert sorted(q["quote_id"] for q in got["quotes"]) == expected
    assert got["count"] == len(expected) > 0
    ages = [q["age_days"] for q in got["quotes"]]
    assert ages == sorted(ages, reverse=True) and min(ages) > 7


def test_open_quotes_over_mcp_matches_function():
    result = asyncio.run(server.call_tool("open_quotes", {"older_than_days": 14}))
    payload = json.loads(result.content[0].text)
    assert payload == json.loads(json.dumps(tools.open_quotes(14)))


def test_find_customer():
    res = tools.find_customer("LOPEZ")
    assert [c["name"] for c in res["matches"]] == ["Maria Lopez"]
    assert res["matches"][0]["customer_id"] == "C001"
    assert tools.find_customer("zzzz")["matches"] == []
    assert "error" in tools.find_customer("a")


def test_get_production_matches_report_script():
    res = tools.get_production("2026-W43")
    expected = skill_runner.report().compute(config.data_dir() / "production" / "production_2026-W43.xlsx")
    assert res["totals"] == expected["totals"]
    assert tools.get_production("latest")["week"] == "2026-W43"
    one = tools.get_production("2026-W43", "Grant")
    assert one["producer"]["producer"] == "Grant Fowler"
    assert len(one["policies"]) == one["producer"]["policies"]
    assert round(sum(p["premium"] for p in one["policies"]), 2) == one["producer"]["premium"]
    assert "error" in tools.get_production("2025-W01")


def test_list_reports():
    res = tools.list_reports()
    assert len(res["production_weeks"]) == 8
    assert res["customers"]["rows"] == 40
