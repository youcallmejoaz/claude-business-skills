# PLAN: Claude Business Setup Kit

A demo build on sample data: Claude set up for a fictional insurance agency, with four Skills, a Claude Project pack, a read-only data connector, a local review app and evals.

## Evidence to feature map

| Feature | Evidence it answers |
|---|---|
| `production-report` skill | "analysing Excel reports and insurance production data", "automating recurring reports" |
| `weekly-owner-brief` skill | "automating recurring reports", "working with Excel and documents" |
| `quote-intake` skill | "quoting ... workflows" |
| `customer-reply` skill | "customer service workflows" |
| Claude Project pack | "Projects for business and personal work", "memory and context", "set up" (7 posts) |
| Skills in Agent Skills format | "reusable Skills", "Claude Skills" (4 posts) |
| Agency data connector (MCP) | "integrations", signal S6: value is wiring into the client's own data |
| Skills Studio app | "specialised assistants", approval rules from S6 |
| Evals | Makes "the same way every time" checkable |

## Architecture

```
 owner ──> Skills Studio (FastAPI + Jinja2 + HTMX, localhost only)
              │
              ├── skills/<name>/scripts/*.py   exact maths and checks (pure Python, pandas)
              ├── agency/llm.py                 writer: Claude (real mode) or recorded fixtures (demo mode)
              ├── agency/guards.py              number placeholders, FAQ citation check, quote source check
              └── connector/tools.py            read-only queries over data/ (same code the MCP server exposes)

 Claude Desktop / Claude Code ──stdio──> connector/server.py (MCP, 4 read-only tools)
 Claude.ai Project <── claude-project/ (instructions + knowledge files, uploaded by hand)
```

Core rule: code computes, Claude writes, a person approves.

- **Numbers:** the report script computes every metric. Claude gets the metric values but must write them as `{{metric_key}}` placeholders. Code fills them in. Any bare digit left in the narrative is flagged and removed.
- **Quotes:** each extracted field carries the exact text it came from. Code checks that text is in the email, and that every date or amount in the value appears in that text. Anything that fails goes to "missing".
- **Replies:** every factual sentence must cite an FAQ id. Code checks the id exists and the sentence overlaps the cited answer. Anything that fails becomes "I'll confirm this with the team." and is flagged.

## Data model (sample data, all fictional)

- `data/production/production_2026-WNN.xlsx` (8 weeks, W36 to W43), sheets:
  - `Production`: Date, Producer, Policy Number, Customer, Line (Auto, Home, Commercial, Life), Business Type (New, Renewal), Written Premium
  - `Renewals Due`: Producer, Policy Number, Line, Expiring Premium, Outcome (Renewed, Lost)
  - `Targets`: Producer, Weekly Premium Target
- `data/customers.csv`: 40 customers (id, name, city, zip, phone, lines held, producer)
- `data/quotes.csv`: open and closed quotes (id, customer, line, producer, requested date, status, last contact)
- `data/quote_emails/*.txt`: 25 messy quote request emails
- `data/customer_messages/*.txt`: sample customer questions for the reply skill
- `claude-project/knowledge/faq.md`: 30 FAQ entries with ids `FAQ-01` to `FAQ-30` (single source of truth, parsed by code)

## Folder layout

```
skills/            four Agent Skills (SKILL.md + scripts/ + reference/)
claude-project/    project instructions, knowledge files, setup guide
connector/         MCP server (stdio) + shared read-only tools
agency/            shared app code: config, llm client, guards, pdf
studio/            FastAPI app, templates, static (htmx vendored)
data/              generated sample data
fixtures/llm/      recorded model responses for demo mode
evals/             12 cases + runner
scripts/           seed, record fixtures, char counts
tests/             pytest
clips/             Playwright recordings, cards, proposal cut
docs/              portfolio entry, cover images
```

## Modes

- `DEMO_MODE=1` (default): no keys, no network. Writer replays `fixtures/llm/`. If an input has no recording, a rule-based draft is shown and labelled as such.
- `DEMO_MODE=0` + `ANTHROPIC_API_KEY`: Sonnet writes reports, briefs and replies; Haiku parses quote emails. Only the fields a skill needs are sent.

## Test plan

- Report totals match hand-calculated values for 3 small fixture weeks.
- Quote intake: required fields present or listed missing; invented dates and amounts are rejected.
- Customer reply: every fact sentence has an existing FAQ citation; uncited facts are replaced and flagged.
- MCP tools: correct rows on fixture data; all tools annotated read-only; data files unchanged after calls.
- Studio: each page and action works end to end in demo mode; PDF export is a valid one page PDF.
- Evals: 12 cases, runner prints pass rate.
- Repo hygiene: no keys, tokens, real emails or personal paths.
- Skills format: frontmatter `name` matches folder, description present.
- CI: GitHub Actions on push runs tests and evals on Python 3.11.

## Build order

1. Plan, CLAUDE.md, tooling (lockfile, Makefile, .env.example, CI)
2. Seed script and sample data, FAQ and project knowledge
3. Skill scripts (report maths, quote checks, citation checks) + tests
4. LLM layer, guards, fixtures
5. MCP connector + tests
6. Skills Studio + PDF + tests
7. Evals
8. README, Docker
9. Clips, proposal cut, portfolio, cover

## Later (not in this build)

- Mapping wizard for a client's own spreadsheet columns
- Scheduled weekly run
- Connector over a live agency management system API
- Multi-user approval log
