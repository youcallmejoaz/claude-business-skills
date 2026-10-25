"""Agency data connector: a local MCP server (stdio) with four read-only tools.

Run:  python -m connector.server
Add to Claude Desktop or Claude Code as a stdio server (see claude-project/SETUP_GUIDE.md).
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

from connector import tools

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

server = MCPServer(
    "agency-data",
    instructions="Read-only access to the agency's production, customer and quote exports. "
                 "Numbers come from the files; never estimate them.",
)


@server.tool(title="List reports", annotations=READ_ONLY)
def list_reports() -> dict:
    """List the exports available: weekly production workbooks, customers and quotes."""
    return tools.list_reports()


@server.tool(title="Get production", annotations=READ_ONLY)
def get_production(period: str = "latest", producer: str | None = None) -> dict:
    """Production numbers for one week. period is an ISO week like '2026-W43' or 'latest'.
    producer (optional) narrows to one producer and lists their policies."""
    return tools.get_production(period, producer)


@server.tool(title="Find customer", annotations=READ_ONLY)
def find_customer(name: str) -> dict:
    """Find customers whose name contains the given text, with their quotes."""
    return tools.find_customer(name)


@server.tool(title="Open quotes", annotations=READ_ONLY)
def open_quotes(older_than_days: int = 7) -> dict:
    """Quotes still open (Open or Quoted) that were requested more than older_than_days ago."""
    return tools.open_quotes(older_than_days)


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
