"""No secrets, real email addresses or personal paths in tracked files, and the skills are well formed."""

import re
import subprocess

from agency import config

TEXT = (".py", ".md", ".txt", ".csv", ".json", ".html", ".css", ".js", ".mjs", ".yml", ".yaml", ".toml",
        ".example", ".in", ".lock", "Makefile", "Dockerfile")
PATTERNS = {
    "Anthropic key": re.compile("sk-" + "ant-"),
    "generic secret": re.compile(r"(?i)(api[_-]?key|secret|token)\s*=\s*['\"]?[A-Za-z0-9_\-]{16,}"),
    "personal path": re.compile("/" + "home/|/" + "Users/|/" + "root/"),
    "GitHub token": re.compile("gh" + "p_[A-Za-z0-9]{20,}"),
}
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
ALLOWED_EMAIL_DOMAINS = ("example.com", "anthropic.com")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=config.ROOT, capture_output=True, text=True, check=True).stdout
    return [config.ROOT / p for p in out.splitlines() if p.endswith(TEXT) and not p.endswith("htmx.min.js")]


def test_no_secrets_or_personal_paths():
    problems = []
    for path in tracked_files():
        if not path.exists():
            continue
        text = path.read_text(errors="ignore")
        for name, pat in PATTERNS.items():
            if pat.search(text):
                problems.append(f"{path.name}: {name}")
        for email in (e.rstrip(".") for e in EMAIL.findall(text)):
            if not email.lower().endswith(ALLOWED_EMAIL_DOMAINS) and not email.startswith("git@"):
                problems.append(f"{path.name}: email {email}")
    assert not problems


def test_skills_have_valid_frontmatter():
    for skill in sorted(config.SKILLS_DIR.iterdir()):
        text = (skill / "SKILL.md").read_text()
        m = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", text, re.S)
        assert m, skill.name
        assert m.group(1) == skill.name
        assert 20 < len(m.group(2)) <= 1024


def test_owner_brief_carries_identical_report_scripts():
    for script in ("compute_report.py", "fill_narrative.py"):
        a = config.SKILLS_DIR / "production-report" / "scripts" / script
        b = config.SKILLS_DIR / "weekly-owner-brief" / "scripts" / script
        assert a.read_text() == b.read_text(), script
