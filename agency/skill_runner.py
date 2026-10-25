"""Load the skills' own scripts so the app runs exactly the code the Claude skills run."""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from types import ModuleType

from agency.config import SKILLS_DIR


@lru_cache(maxsize=None)
def load(skill: str, script: str) -> ModuleType:
    path = SKILLS_DIR / skill / "scripts" / f"{script}.py"
    name = f"skill_{skill.replace('-', '_')}_{script}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def report():
    return load("production-report", "compute_report")


def narrative():
    return load("production-report", "fill_narrative")


def brief():
    return load("weekly-owner-brief", "build_brief")


def quote():
    return load("quote-intake", "check_quote")


def reply():
    return load("customer-reply", "check_reply")
