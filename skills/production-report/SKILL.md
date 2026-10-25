---
name: production-report
description: Turns the producers' weekly production spreadsheet (Excel) into the agency owner's weekly production report. A script calculates premium written, policies by line, new vs renewal, retention and performance against target exactly; Claude only writes the explanation and flags. Use when someone shares a weekly production export or asks how the agency or a producer did this week.
---

# Weekly production report

## When to use
The owner or office manager shares this week's production spreadsheet, or asks "how did we do this week?", "who is behind target?", "what was retention?".

## Steps
1. Run the calculation. Never add up numbers yourself.
   ```
   python scripts/compute_report.py <this_week.xlsx> --previous <last_week.xlsx> --json > report.json
   python scripts/compute_report.py <this_week.xlsx> --previous <last_week.xlsx>
   ```
   `--previous` is optional; without it there is no week-on-week change.
2. Show the tables from the second command exactly as printed. They are the numbers the report uses.
3. Write the narrative: a one-line headline and two short paragraphs for a busy owner.
   - Use numbers **only** through placeholders from `report.json` → `metrics`, for example `{{total_premium}}`, `{{retention_rate}}`, `{{producer.grant_fowler.pct_of_target}}`, `{{line.auto.policies}}`. Do not type any digit yourself.
   - Explain each flag in `report.json` → `flags` in plain words. Do not invent new flags or causes; if the reason is unknown, say the owner may want to ask the producer.
   - If `data_issues` is not empty, say which rows were skipped.
4. Fill and check the narrative:
   ```
   python scripts/fill_narrative.py report.json narrative.txt
   ```
   It swaps placeholders for the computed values and removes any sentence with a number that did not come from the script. Fix and rerun if it prints a FLAG.
5. Present: headline, filled narrative, tables, flags. End with: "Draft for review. Nothing has been sent."

## Rules
- Numbers come from the script, never from you.
- Thresholds (below 80% of target is red, 120% or more is green, retention under 85% is amber, a drop of 10% or more on last week is amber) are set in `scripts/compute_report.py`.
- Do not name a reason for poor performance that is not in the data.

## Spreadsheet format
See `reference/columns.md`. A real agency's export usually needs its column names mapped once before first use.
