"""Settings from the environment (and .env when present). See .env.example for every variable."""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:  # python-dotenv is optional
    pass


def _flag(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def demo_mode() -> bool:
    return _flag("DEMO_MODE", "1")


def api_key() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or None


WRITER_MODEL = os.environ.get("WRITER_MODEL", "claude-sonnet-5-5")
INTAKE_MODEL = os.environ.get("INTAKE_MODEL", "claude-haiku-5-5")
AGENCY_NAME = "Fernhill Insurance Agency"

SKILLS_DIR = ROOT / "skills"
FIXTURES_DIR = ROOT / "fixtures" / "llm"
KNOWLEDGE_DIR = ROOT / "claude-project" / "knowledge"


def data_dir() -> Path:
    p = Path(os.environ.get("AGENCY_DATA_DIR", "data"))
    return p if p.is_absolute() else ROOT / p


def as_of_date() -> dt.date:
    value = os.environ.get("AS_OF_DATE", "2026-10-23").strip()
    if value:
        return dt.date.fromisoformat(value)
    return dt.date.today()
