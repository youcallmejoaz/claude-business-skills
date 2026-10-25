"""Check a drafted customer reply so every fact comes from the agency FAQ.

Claude drafts the reply as a list of sentences. Each sentence has a type:
  fact      states something about the agency or a policy; must cite FAQ ids
  courtesy  greeting-style filler with no facts ("Thanks for getting in touch.")
  confirm   "I'll confirm this with the team" for anything the FAQ does not answer

This script:
  - checks every cited FAQ id exists,
  - checks each fact sentence matches its cited entries (shared words, and every
    number in the sentence appears in a cited answer),
  - treats a "courtesy" sentence with numbers or policy words as an uncited fact,
  - replaces any sentence that fails with "I'll confirm this with the team" and flags it.

Usage:
    python check_reply.py draft.json [faq.md]
    python check_reply.py --search "how late are you open on saturday" [faq.md]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FAQ_FILE = HERE.parent / "reference" / "faq.md"
CONFIRM = "I'll confirm this with the team and get back to you."
MIN_OVERLAP = 0.5

STOP = set("""a about above after again all also am an and any are as at be because been before being both but by
can could did do does doing down during each few for from further had has have having he her here hers him his how
i if in into is it its just me more most my no nor not now of off on once only or other our out over own same she
should so some such than that the their them then there these they this those through to too under until up very was
we were what when where which while who whom why will with would you your yours yes we're you're it's i'm i'll we'll
please thanks thank hi hello dear regards best let know get like need want just also sure""".split())
POLICY_WORDS = {"cover", "covers", "covered", "coverage", "premium", "price", "cost", "costs", "discount", "deductible",
                "refund", "claim", "claims", "rate", "rates", "days", "hours", "open", "closed", "carrier",
                "carriers", "pay", "payment", "fee", "free", "guarantee", "guaranteed", "cheaper", "approved"}


def parse_faq(path: Path = FAQ_FILE) -> dict:
    faq, current = {}, None
    for line in Path(path).read_text().splitlines():
        m = re.match(r"^## (FAQ-\d{2}): (.+)$", line.strip())
        if m:
            current = m.group(1)
            faq[current] = {"id": current, "question": m.group(2).strip(), "answer": ""}
        elif current and line.strip():
            faq[current]["answer"] = (faq[current]["answer"] + " " + line.strip()).strip()
    return faq


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower().replace("’", "'"))
            if len(w) >= 3 and w not in STOP}


def stem(w: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[: -len(suffix)]
    return w


def overlap(sentence: str, reference: str) -> float:
    s = {stem(w) for w in words(sentence)}
    if not s:
        return 1.0
    r = {stem(w) for w in words(reference)}
    return len(s & r) / len(s)


def numbers(text: str) -> list[str]:
    return re.findall(r"\d+", re.sub(r"(?<=\d),(?=\d{3})", "", text))


def search(question: str, faq: dict, k: int = 3, min_score: float = 0.2) -> list[dict]:
    """Rank FAQ entries by shared words with the question. Used to find candidates, not to answer."""
    q = {stem(w) for w in words(question)}
    scored = []
    for entry in faq.values():
        qset = {stem(w) for w in words(entry["question"])}
        aset = {stem(w) for w in words(entry["answer"])}
        if not q:
            continue
        score = (2 * len(q & qset) + len(q & aset)) / (2 * len(q))
        if score >= min_score:
            scored.append({**entry, "score": round(score, 3)})
    return sorted(scored, key=lambda e: -e["score"])[:k]


def check_sentence(s: dict, faq: dict) -> str | None:
    """Return None if the sentence is acceptable, else the reason it is not."""
    text = s.get("text", "").strip()
    kind = s.get("type", "fact")
    ids = s.get("faq_ids") or []
    if kind == "confirm":
        if "confirm" not in text.lower():
            return "confirm sentence does not say we will confirm"
        if numbers(text):
            return "confirm sentence contains a number"
        return None
    if kind == "courtesy" and not ids:
        if numbers(text) or (words(text) & POLICY_WORDS):
            return "states a fact without an FAQ citation"
        return None
    if not ids:
        return "fact with no FAQ citation"
    unknown = [i for i in ids if i not in faq]
    if unknown:
        return f"cites FAQ entries that do not exist: {unknown}"
    reference = " ".join(faq[i]["question"] + " " + faq[i]["answer"] for i in ids)
    extra_numbers = [n for n in numbers(text) if n not in numbers(reference)]
    if extra_numbers:
        return f"number(s) {extra_numbers} are not in the cited FAQ entries"
    if overlap(text, reference) < MIN_OVERLAP:
        return "does not match what the cited FAQ entries say"
    return None


def check(draft: dict, faq: dict | None = None) -> dict:
    faq = faq or parse_faq()
    out, flags = [], []
    for s in draft.get("sentences", []):
        reason = check_sentence(s, faq)
        if reason:
            flags.append({"sentence": s.get("text", ""), "reason": reason})
            if out and out[-1]["type"] == "confirm" and out[-1]["text"] == CONFIRM:
                continue
            out.append({"text": CONFIRM, "type": "confirm", "faq_ids": [], "replaced": True, "reason": reason})
        else:
            out.append({"text": s["text"].strip(), "type": s.get("type", "fact"),
                        "faq_ids": list(s.get("faq_ids") or []), "replaced": False})
            if s.get("type") == "confirm":
                flags.append({"sentence": s["text"].strip(), "reason": "needs an answer from the team"})
    greeting = draft.get("greeting", "").strip()
    sign_off = draft.get("sign_off", "Best regards,\nFernhill Insurance Agency").strip()
    body = " ".join(s["text"] for s in out)
    cited = sorted({i for s in out for i in s["faq_ids"]})
    return {
        "sentences": out,
        "flags": flags,
        "citations": [{"id": i, "question": faq[i]["question"], "answer": faq[i]["answer"]} for i in cited],
        "reply_text": "\n\n".join(p for p in (greeting, body, sign_off) if p),
        "greeting": greeting,
        "sign_off": sign_off,
        "all_facts_cited": all(s["type"] != "fact" or s["faq_ids"] for s in out),
    }


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "--search":
        faq = parse_faq(Path(argv[2])) if len(argv) > 2 else parse_faq()
        print(json.dumps(search(argv[1], faq), indent=2))
        return 0
    if not argv:
        print(__doc__)
        return 2
    faq = parse_faq(Path(argv[1])) if len(argv) > 1 else parse_faq()
    result = check(json.loads(Path(argv[0]).read_text()), faq)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
