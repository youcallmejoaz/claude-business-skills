# Clip manifest

All clips: 1920 x 1080, 30 fps, H.264 (yuv420p), no audio. Recorded in demo mode with the seeded sample data by `clips/record.mjs`. Stills: `clips/frames/` (one per clip) and `clips/cards/*.png` (cards and prompt replays).

| Clip ID | File | Duration | What it shows | Video section |
|---|---|---|---|---|
| K01 | `K01_problem.mp4` | 6.5 s | Card: Monday morning, 6 producers, one spreadsheet, two hours of copy and paste | Problem |
| P01 | `P01_setup_prompt.mp4` | 10.5 s | Prompt replay: SHOW prompt 1 typed, plan summary appears | Setup |
| C01 | `C01_upload.mp4` | 6.8 s | Skills Studio: production report, weekly Excel file dropped in | Result |
| C02 | `C02_report.mp4` | 12.6 s | Report runs: numbers table on the left, narrative and flags on the right | Result |
| C03 | `C03_flag_closeup.mp4` | 4.5 s | Close-up: red flag on the producer below target | Result |
| C04 | `C04_owner_brief.mp4` | 12.2 s | Owner brief: one-page PDF scrolls, email draft next to it | Result |
| K02 | `K02_flow.mp4` | 8.5 s | Card: file in, script does the maths, Claude writes, a person approves | How it works |
| C05 | `C05_quote_intake.mp4` | 13.5 s | Quote intake: messy email pasted, structured fields fill in, missing info list | Result |
| C06 | `C06_citation_closeup.mp4` | 4.3 s | Close-up: customer reply with the FAQ-08 citation and its source highlighted | Safeguards |
| P02 | `P02_skill_prompt.mp4` | 8.9 s | Prompt replay: SHOW prompt 2 typed, the production-report skill folder appears | Setup |
| C07 | `C07_evals.mp4` | 9.7 s | Evals page: 12 cases run, 12/12 pass rate shown | Safeguards |
| C08 | `C08_connector.mp4` | 13.7 s | Data connector: 'show open quotes older than 7 days', tool call and table | Result |
| K03 | `K03_safeguards.mp4` | 7.5 s | Card: exact numbers, FAQ-only answers, drafts not sends | Safeguards |
| K04 | `K04_offer.mp4` | 7.5 s | Card: what a version for your agency includes, set up in a week, cost as an estimate | Offer |

Re-record everything with `make clips` (needs the venv and Playwright's Chromium). Raw recordings go to `clips/raw/`, which is not committed.
