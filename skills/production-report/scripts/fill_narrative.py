"""Fill {{placeholders}} in Claude's narrative with numbers from compute_report.py, and refuse bare numbers.

Claude writes the narrative with placeholders such as {{total_premium}} or
{{producer.grant_fowler.pct_of_target}}. This script swaps in the computed values.
Any digit Claude typed itself is treated as unverified: the sentence is removed and flagged.

Usage:
    python fill_narrative.py report.json narrative.txt
"""

from __future__ import annotations

import json
import re
import sys

PLACEHOLDER = re.compile(r"\{\{\s*([a-z0-9_.]+)\s*\}\}")
SENTENCE = re.compile(r"(?<=[.!?])\s+")


def fill(text: str, metrics: dict) -> tuple[str, list[str]]:
    """Return (filled text, problems). Unknown placeholders and bare digits are problems."""
    problems: list[str] = []
    kept = []
    for sentence in SENTENCE.split(text.strip()):
        if not sentence:
            continue
        unknown = [k for k in PLACEHOLDER.findall(sentence) if k not in metrics]
        bare = re.findall(r"\d", PLACEHOLDER.sub("", sentence))
        if unknown:
            problems.append(f"Removed a sentence with unknown placeholder(s) {unknown}: \"{sentence}\"")
            continue
        if bare:
            problems.append(f"Removed a sentence with a number not taken from the report: \"{sentence}\"")
            continue
        kept.append(PLACEHOLDER.sub(lambda m: metrics[m.group(1)], sentence))
    return " ".join(kept), problems


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2:
        print(__doc__)
        return 2
    report = json.load(open(argv[0]))
    text = open(argv[1]).read()
    filled, problems = fill(text, report["metrics"])
    print(filled)
    for p in problems:
        print(f"FLAG: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
