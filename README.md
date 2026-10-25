# Claude Business Setup Kit

**Claude set up as a trained assistant for a service agency.** It reads the weekly production spreadsheet, writes the owner's report, turns messy quote emails into clean requests, and drafts customer replies from the agency's own FAQ, the same way every time.

This is a demo build on sample data. The agency, its producers, customers and numbers are all made up.

## The problem

Every Monday someone in the agency spends hours turning the producers' spreadsheet into a report. Quote emails arrive half complete and wait for someone to work out what is missing. Customer questions get answered from memory, so the answers vary.

Most agencies already pay for Claude but only use it as a chat box. The value is in wiring it into the agency's own spreadsheet, checklist, FAQ and approval rules.

## What it does

| Skill | In | Out |
|---|---|---|
| Production report | The weekly production spreadsheet | Premium written, policies by line, new vs renewal, retention and performance against target, with a plain-English explanation and flags |
| Owner brief | The same spreadsheet | A one-page PDF and an email draft for the team |
| Quote intake | A messy customer email | A structured quote request, plus the missing information and the exact questions to ask |
| Customer reply | A customer's question | A reply in the agency's tone, using only the FAQ, with the FAQ entry shown for every fact |

Plus:
- **A Claude Project pack**: instructions and knowledge files (FAQ, tone guide, carriers, service area, quote checklist) with a short setup guide.
- **A data connector**: lets Claude Desktop or Claude Code read the agency's exports (production, customers, open quotes). It can only read.
- **Skills Studio**: a local app to run each skill, check the result next to its numbers and sources, approve it, and export or copy it.
- **Evals**: 12 test cases that prove the numbers, quote fields and FAQ citations are right.

## How it works, in 4 steps

1. **Add the file or paste the email.** Drop this week's spreadsheet into Skills Studio, or paste a quote request or customer email.
2. **A script does the exact work.** It calculates every number, checks every quote field against the email and looks up the FAQ.
3. **Claude writes the draft.** The explanation, the owner email, the structured request or the reply.
4. **A person approves it.** You see the draft next to the numbers and sources, then export or copy it yourself.

## Safeguards

- **Numbers come from code, never from Claude.** Claude writes `{{total_premium}}`, not "$72,318", and code fills in the value. Any number Claude types itself is removed and flagged. The report always shows the table it used.
- **Replies only use the FAQ.** Every fact must cite an FAQ entry that exists and says it. Anything else is replaced with "I'll confirm this with the team and get back to you." and flagged for a person.
- **Quote intake never guesses.** Every field must quote the words it came from in the email. A date or amount that is not in the email is rejected and listed as missing.
- **Nothing is sent.** There is no send button anywhere. Everything is a draft a person approves, then copies or downloads.
- **No data leaves the computer in demo mode.** In real mode, only what a skill needs is sent to Claude: for the report, the computed totals and flags, not the customer rows.
- **The connector is read-only.** Its four tools are marked read-only and a test checks the data files are unchanged after every call.

## Demo

- Proposal cut (60 to 90 seconds): `clips/proposal_cut.mp4`
- Full video: _YouTube link to add_
- Clip list: `clips/MANIFEST.md`

## Try it

You need Python 3.11 or newer.

```
make install    # creates .venv and installs the pinned, hash-checked dependencies
make dev        # opens Skills Studio on http://127.0.0.1:8000
```

Demo mode is on by default: no API key, no network, sample data and recorded responses. Or with Docker:

```
docker compose up
```

To use Claude for real, copy `.env.example` to `.env`, set `DEMO_MODE=0` and add your `ANTHROPIC_API_KEY`. Claude Sonnet writes the reports, briefs and replies; Claude Haiku reads the quote emails and picks connector tools.

Other commands:

```
make seed            # regenerate the sample data (same result every time)
make test            # run the tests
make evals           # run the 12 evals and print the pass rate
make mcp             # run the data connector (stdio) for Claude Desktop or Claude Code
make package-skills  # zip each skill for upload to Claude
```

To add the kit to Claude itself (Project, Skills, connector), follow `claude-project/SETUP_GUIDE.md`.

## Architecture

```
skills/              four Agent Skills: SKILL.md + scripts (the maths and checks) + reference files
  production-report    compute_report.py, fill_narrative.py
  weekly-owner-brief   build_brief.py (+ copies of the report scripts so it works alone)
  quote-intake         check_quote.py, reference/quote-checklist.md
  customer-reply       check_reply.py, reference/faq.md
claude-project/      Project instructions, knowledge files, setup guide
connector/           read-only tools (tools.py) and the MCP server (server.py)
agency/              shared app code: writer (Claude or recorded), services, PDF
studio/              Skills Studio: FastAPI + Jinja2 + HTMX, no frontend build step
evals/               12 cases and the runner
data/                sample agency data (generated by scripts/seed.py)
fixtures/llm/        recorded responses used in demo mode
```

Skills Studio and the evals run the skills' own scripts, so the app, the evals and Claude all use the same code.

**About the demo responses.** The responses in `fixtures/llm/` were written for this sample data in the same format Claude returns, and pass the same checks. One reply (the towing question) deliberately contains an unsupported promise, to show the check catching it. Run `make record-fixtures` with an API key to replace them with live recordings. If you paste something that has no recording, demo mode shows a simple rule-based draft and labels it as such.

## Tests

`make test` runs the test suite: report totals against hand-calculated values for 3 small fixture weeks, the quote and reply checks (including invented dates, made-up amounts, fake citations and facts hidden in polite sentences), the connector's rows and read-only behaviour, the app end to end in demo mode, the evals, and a scan for secrets and personal data. GitHub Actions runs the tests and evals on every push.

## Honest limits

- The sample agency and data are fictional. A real setup first maps the agency's own spreadsheet columns (see `skills/production-report/reference/columns.md`) and swaps in its own FAQ, tone guide and checklist.
- Claude Skills behave slightly differently across Claude apps; `claude-project/SETUP_GUIDE.md` notes where.
- The demo responses were written for the sample data, not recorded from the API. Real mode needs an API key and has not been run against the live API in this build.
- Running cost (estimate): a few cents per report in real mode, plus the agency's Claude plan.
