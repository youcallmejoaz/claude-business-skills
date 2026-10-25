---
name: quote-intake
description: Turns a messy customer quote request email (missing details, mixed lines, forwarded threads) into a clean, structured quote request for a producer, plus a list of missing information with the exact questions to ask the customer. Never guesses a value. Use when someone pastes or forwards a quote request email for auto, home, commercial or life insurance.
---

# Quote intake

## When to use
A customer emails asking for a quote, often with half the details, and the producer needs a clean request and a list of what to ask for.

## Steps
1. Read the email, including any forwarded part.
2. Write `extraction.json`. For every field you can find, give the value **and the exact words from the email it came from**:
   ```json
   {"fields": {
      "customer_name": {"value": "Maria Lopez", "source": "Thanks, Maria Lopez"},
      "effective_date": {"value": "Nov 1st", "source": "need it to start Nov 1st"}
    },
    "notes": "anything useful that is not a field"}
   ```
   Field keys and which lines need them are in `reference/quote-checklist.md`.
   - Write dates and amounts exactly as the customer wrote them. Do not convert "next Friday" into a date.
   - If a value is not in the email, leave the field out. Never guess.
   - `line_of_business` lists every line asked for, for example "Auto and Home".
3. Check it:
   ```
   python scripts/check_quote.py email.txt extraction.json
   ```
   The script drops any field whose source is not in the email, or whose value has a number or month not in its source, and lists every required field that is missing with the question to ask.
4. Present the structured request (field, value, source), then "Missing information" with the questions, ready to paste into a reply. Say: "Draft for review. Nothing has been sent."

## Rules
- Only the script decides what is missing; do not add or remove items yourself.
- ZIP codes outside `reference/service-area.md`: note it for the producer; do not tell the customer we cannot help.
