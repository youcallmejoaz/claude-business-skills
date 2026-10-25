---
name: weekly-owner-brief
description: Produces the agency owner's one-page weekly brief as a PDF plus a short email draft, from the weekly production spreadsheet. Numbers come from the production report script; Claude writes the headline, three key points, next steps and the email. Use when the owner wants the Monday summary, a one-pager, or an email they can forward to the team.
---

# Weekly owner brief

## When to use
"Make me the weekly one-pager", "draft the Monday email to the team", "send me the owner brief for last week".

## Steps
1. Calculate the numbers (never by hand):
   ```
   python scripts/compute_report.py <this_week.xlsx> --previous <last_week.xlsx> --json > report.json
   ```
2. Write `brief.json` with numbers only as placeholders from `report.json` → `metrics` (for example `{{total_premium}}`, `{{producer.grant_fowler.pct_of_target}}`). Do not type digits.
   ```json
   {"headline": "one line, outcome first",
    "bullets": ["three short points: overall result, who stood out, what needs attention"],
    "actions": ["up to three concrete next steps for the owner, based only on the flags"],
    "email_subject": "Weekly production: week ending {{week_ending}}",
    "email_body": "Short email to the team, 4 to 7 sentences, in the tone guide's voice"}
   ```
   Base points and actions on `flags`. Do not invent causes. Follow `reference/tone-guide.md`.
3. Build the PDF and check the wording:
   ```
   python scripts/build_brief.py report.json brief.json --out owner_brief.pdf
   ```
   Any sentence with a number that did not come from the script is removed and printed as a FLAG. Fix it and rerun.
4. Share the PDF and the email draft. Say: "Draft for review. Nothing has been sent."

## Rules
- One page. If it spills over, shorten the bullets.
- The email is a draft. Never send it.
- `compute_report.py` and `fill_narrative.py` here are copies of the production-report skill's scripts, so this skill works on its own.
