"""Count characters for each Upwork field and write the counts into the file.

Fields are marked like this in docs/UPWORK_PORTFOLIO.md:
    <!-- count:title max=70 -->
    the text
    <!-- /count -->
    Characters: 53 / 70
The "Characters:" line after each block is rewritten. Exits 1 if any field is over its limit.
"""

import re
import sys
from pathlib import Path

BLOCK = re.compile(r"<!-- count:(\S+) max=(\d+) -->\n(.*?)\n<!-- /count -->\n(Characters: [^\n]*\n)?", re.S)


def main(path: str) -> int:
    p = Path(path)
    text = p.read_text()
    over = []

    def repl(m: re.Match) -> str:
        name, limit, body = m.group(1), int(m.group(2)), m.group(3).strip()
        n = len(body)
        status = "OK" if n <= limit else "OVER"
        if n > limit:
            over.append(name)
        print(f"{name}: {n} / {limit} {status}")
        return f"<!-- count:{name} max={limit} -->\n{body}\n<!-- /count -->\nCharacters: {n} / {limit}\n"

    p.write_text(BLOCK.sub(repl, text))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/UPWORK_PORTFOLIO.md"))
