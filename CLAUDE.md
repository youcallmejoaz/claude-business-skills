# CLAUDE.md

Claude Business Setup Kit: a demo build on sample data that sets Claude up for a fictional insurance agency. Four Agent Skills, a Claude Project pack, a read-only MCP data connector over CSV and Excel exports, a local review app (Skills Studio) and evals.

## Folder map

- `skills/<name>/` Agent Skills: `SKILL.md`, `scripts/` (exact maths and checks), `reference/`
- `claude-project/` project instructions, knowledge files (FAQ is the source of truth), setup guide
- `connector/` MCP server (stdio). `tools.py` holds the read-only queries; `server.py` exposes them
- `agency/` shared app code: `config.py`, `llm.py` (Claude or recorded replay), `services.py` (one function per skill), `offline.py` (rule-based demo drafts), `pdf.py`, `skill_runner.py`. The checks themselves live in the skills' scripts
- `studio/` FastAPI + Jinja2 + HTMX app, no frontend build step
- `data/` generated sample data (fictional). `fixtures/llm/` recorded model responses for demo mode
- `evals/` 12 cases and the runner. `tests/` pytest. `scripts/` seed and helpers
- `clips/` video recordings and cards. `docs/` portfolio entry and cover images

## Commands

```
make install     # venv + pip install -r requirements.lock (hash-checked)
make seed        # regenerate sample data (deterministic)
make dev         # Skills Studio on http://127.0.0.1:8000 (demo mode)
make test        # pytest
make evals       # 12 eval cases, prints pass rate
make mcp         # run the MCP connector on stdio
make package-skills  # zip each skill for upload to Claude
docker compose up
```

## Conventions

- Python 3.11 target (CI), works on 3.13. Dependencies pinned in `requirements.lock`; add to `requirements.in` and recompile with `uv pip compile requirements.in --python-version 3.11 --generate-hashes -o requirements.lock`.
- Skill scripts are standalone (stdlib + pandas + openpyxl only) so they run inside Claude's code tool. The app loads them with `agency/skill_runner.py`; never duplicate their logic.
- Models: `claude-sonnet-5-5` for writing, `claude-haiku-5-5` for intake parsing. Structured JSON via `output_config.format`.
- Writing rules for anything user-facing: no em dashes, no emojis, plain words, "in a week" never "in weeks", no claims the build does not prove.

## Hard rules (guardrails)

1. Numbers come from code, never from the model. The narrative uses `{{metric}}` placeholders; bare digits are flagged and stripped. The report always shows the table it used.
2. Customer replies only state facts that exist in the FAQ, each with a citation. Anything else becomes "I'll confirm this with the team." and is flagged.
3. Quote intake never invents a value. Every field must quote its source text; dates and amounts must appear in it. Otherwise the field is listed as missing.
4. No personal data leaves the machine in demo mode. Real mode sends only the fields a skill needs.
5. Nothing is emailed or sent. Everything is a draft a person approves.
6. The connector is read-only. No tool writes, deletes or sends.
7. Never commit secrets. `.env` is git-ignored; `.env.example` documents every variable. No real names, emails, client details or personal paths in the repo.
