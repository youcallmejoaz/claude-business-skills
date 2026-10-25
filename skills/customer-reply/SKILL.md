---
name: customer-reply
description: Drafts a reply to a customer email in the agency's tone using only facts from the agency FAQ, citing the FAQ entry for every fact. Anything the FAQ does not answer becomes "I'll confirm this with the team" and is flagged for a person. Use when someone pastes a customer question about hours, payments, policy changes, claims, documents or coverage.
---

# Customer reply

## When to use
A customer asks a question by email and the team wants a reply drafted from the agency's own answers.

## Steps
1. Find the relevant FAQ entries in `reference/faq.md` (helper: `python scripts/check_reply.py --search "<question>"`).
2. Write `draft.json` as a list of sentences, each with a type:
   ```json
   {"greeting": "Hi Maria,",
    "sentences": [
      {"text": "Thanks for getting in touch.", "type": "courtesy", "faq_ids": []},
      {"text": "Our office is open on Saturdays from 9:00 am to 12:00 pm.", "type": "fact", "faq_ids": ["FAQ-01"]},
      {"text": "I'll confirm whether that applies to your policy with the team and get back to you.", "type": "confirm", "faq_ids": []}
    ],
    "sign_off": "Best regards,\nFernhill Insurance Agency"}
   ```
   - `fact`: anything about the agency, prices, coverage, times, steps. Must cite the FAQ ids it comes from and say no more than they say.
   - `courtesy`: thanks or greetings only, no facts.
   - `confirm`: for every question the FAQ does not answer. Start with "I'll confirm" and only promise to check; no facts. Never guess.
3. Check it:
   ```
   python scripts/check_reply.py draft.json
   ```
   Sentences that cite a missing entry, add numbers, or drift from the FAQ are replaced with "I'll confirm this with the team and get back to you." and flagged.
4. Show the reply text, the citations (id and FAQ question) and the flags. Say: "Draft for review. Nothing has been sent."

## Rules
- Follow `reference/tone-guide.md`.
- Never promise coverage, prices or claim outcomes.
