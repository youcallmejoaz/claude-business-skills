# Proposal cut: script

60 to 90 seconds for Upwork proposals: the problem, the result working, the safeguards, the offer.
Built only from the Phase 3 clips. Voice: Kokoro TTS (open weights, Apache 2.0), voice `am_michael`, speed 1.0.
No captions or subtitles, no music, no watermark. The narrator never says a name or gives contact details.

| Scene | Clips | Narration |
|---|---|---|
| 1 | K01 | Every Monday, someone in your agency spends hours turning a spreadsheet into a report. And quote emails sit there, half complete. |
| 2 | C01, C02 | Here, Claude is set up for your agency. Drop in the weekly production file, and the report is ready, with every number calculated exactly. The numbers sit right next to the explanation, so you can check every figure. |
| 3 | C03, C04 | It flags who is behind target, and writes the owner brief and the email, ready for you to check. |
| 4 | C05 | Messy quote requests become clean, structured quotes, with a list of what is still missing. |
| 5 | C06 | Customer replies are drafted from your own answers, and every fact points back to its source. |
| 6 | C07, K03 | Each skill is tested, and nothing is sent without a person approving it. |
| 7 | K04 | If you want Claude working like this inside your business, reply to this proposal, and we can map it to your workflow. |

Scene 2 has one sentence added to the brief's narration ("The numbers sit right next to the explanation, so you can check every figure.") so the cut reaches 60 seconds.

Timing: each scene lasts its narration plus 0.5 seconds. Clips are trimmed to fit, or hold their last frame when short; footage is never sped up by more than 1.25x. Hard cuts, with a 0.3 second crossfade from a card into UI. A slow 5 percent push-in on any shot longer than 8 seconds. Voice normalised to about -16 LUFS.

Rendered by `clips/make_proposal_cut.py`.
