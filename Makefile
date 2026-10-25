PY ?= .venv/bin/python
export DEMO_MODE ?= 1

.PHONY: install seed dev test evals mcp record-fixtures clips counts package-skills

install:
	python3 -m venv .venv
	.venv/bin/pip install --require-hashes -r requirements.lock

seed:
	$(PY) scripts/seed.py

dev:
	$(PY) -m uvicorn studio.app:app --host $${STUDIO_HOST:-127.0.0.1} --port $${STUDIO_PORT:-8000}

test:
	$(PY) -m pytest

evals:
	$(PY) -m evals.run_evals

mcp:
	$(PY) -m connector.server

record-fixtures:
	DEMO_MODE=0 $(PY) scripts/record_fixtures.py

clips:
	node clips/record.mjs

counts:
	$(PY) scripts/count_chars.py docs/UPWORK_PORTFOLIO.md

package-skills:
	$(PY) scripts/package_skills.py
