"""Build the one-page weekly owner brief (PDF) and the email draft.

Inputs:
  report.json  from compute_report.py (all numbers)
  brief.json   Claude's wording, with numbers only as {{placeholders}}:
               {"headline": "...", "bullets": ["...", "...", "..."], "actions": ["..."],
                "email_subject": "...", "email_body": "..."}

Usage:
    python build_brief.py report.json brief.json --out owner_brief.pdf [--html owner_brief.html]

Writes the PDF with WeasyPrint when it is installed; otherwise writes the HTML only,
which any browser can print to PDF. Prints the filled email draft. Nothing is sent.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fill_narrative import fill  # noqa: E402  (copied from the production-report skill)

AGENCY = "Fernhill Insurance Agency"
TEXT_FIELDS = ["headline", "email_subject", "email_body"]
LIST_FIELDS = ["bullets", "actions"]


def fill_brief(brief: dict, metrics: dict) -> tuple[dict, list[str]]:
    """Fill every text field. Email paragraphs are filled one by one to keep line breaks."""
    out, problems = {}, []
    for key in TEXT_FIELDS:
        paragraphs = []
        for para in str(brief.get(key, "")).split("\n"):
            if not para.strip():
                paragraphs.append("")
                continue
            text, p = fill(para, metrics)
            problems += p
            paragraphs.append(text)
        out[key] = "\n".join(paragraphs).strip()
    for key in LIST_FIELDS:
        items = []
        for item in brief.get(key, []):
            text, p = fill(item, metrics)
            problems += p
            if text:
                items.append(text)
        out[key] = items
    return out, problems


from compute_report import money as _money, pct as _pct  # noqa: E402  (same rounding as the report)


def _status(p: dict) -> tuple[str, str]:
    v = p.get("pct_of_target")
    if v is None:
        return "No target", "muted"
    if v < 80:
        return "Below target", "red"
    if v >= 120:
        return "Well ahead", "green"
    return "On track", "ok"


CSS = """
@page { size: Letter; margin: 0.55in 0.6in; }
* { box-sizing: border-box; }
body { font-family: Inter, "DejaVu Sans", Arial, sans-serif; color: #14201b; font-size: 10.5pt; margin: 0; }
.top { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 3px solid #1f7a4d; padding-bottom: 8px; }
.top .agency { font-weight: 700; font-size: 11pt; letter-spacing: 0.02em; }
.top .week { color: #4a5a52; font-size: 10pt; }
h1 { font-size: 19pt; line-height: 1.2; margin: 14px 0 12px; }
.kpis { display: flex; gap: 10px; margin-bottom: 14px; }
.kpi { flex: 1; border: 1px solid #d7e2dc; border-radius: 8px; padding: 10px 12px; }
.kpi .label { color: #4a5a52; font-size: 8.5pt; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi .value { font-size: 17pt; font-weight: 700; margin-top: 2px; }
.kpi .sub { color: #4a5a52; font-size: 8.5pt; }
h2 { font-size: 11pt; margin: 14px 0 6px; color: #1f7a4d; text-transform: uppercase; letter-spacing: 0.05em; }
ul { margin: 0; padding-left: 18px; }
li { margin-bottom: 4px; line-height: 1.4; }
table { width: 100%; border-collapse: collapse; font-size: 9.5pt; }
th { text-align: left; color: #4a5a52; font-weight: 600; border-bottom: 1px solid #d7e2dc; padding: 5px 6px; }
td { border-bottom: 1px solid #eef3f0; padding: 5px 6px; }
td.num, th.num { text-align: right; }
.pill { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 8.5pt; font-weight: 600; }
.pill.red { background: #fde7e7; color: #b42318; }
.pill.green { background: #e3f4ea; color: #1f7a4d; }
.pill.ok { background: #eef3f0; color: #33433b; }
.pill.muted { background: #f2f2f2; color: #666; }
.flag { padding: 6px 10px; border-left: 4px solid #d9a21b; background: #fdf6e3; margin-bottom: 5px; line-height: 1.35; }
.flag.red { border-color: #b42318; background: #fdecec; }
.flag.green { border-color: #1f7a4d; background: #e9f6ee; }
.cols { display: flex; gap: 18px; }
.cols > div { flex: 1; }
.foot { margin-top: 14px; color: #6b7a72; font-size: 8pt; border-top: 1px solid #d7e2dc; padding-top: 6px; }
"""


def render_html(report: dict, brief: dict, agency: str = AGENCY) -> str:
    t = report["totals"]
    e = html.escape
    week_end = report.get("week_ending")
    try:
        week_text = dt.date.fromisoformat(week_end).strftime("%B %-d, %Y")
    except (TypeError, ValueError):
        week_text = report["week"]
    wow = ""
    if t.get("wow_change_pct") is not None:
        c = t["wow_change_pct"]
        wow = f"{'Up' if c > 0 else 'Down'} {_pct(abs(c))} on last week" if _pct(abs(c)) != "0%" else "Level with last week"
    kpis = [
        ("Premium written", _money(t["total_premium"]), wow or f"Target {_money(t['target_total'])}"),
        ("Policies written", str(t["policies_written"]), f"{t['new_policies']} new, {t['renewal_policies']} renewal"),
        ("Retention", _pct(t["retention_rate"]), f"{t['renewals_kept']} of {t['renewals_due']} renewals kept"),
        ("Vs target", _pct(t["pct_of_target"]), f"of {_money(t['target_total'])}"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="label">{e(a)}</div><div class="value">{e(b)}</div>'
        f'<div class="sub">{e(c)}</div></div>' for a, b, c in kpis)
    rows = []
    for p in report["by_producer"]:
        label, cls = _status(p)
        rows.append(f"<tr><td>{e(p['producer'])}</td><td class='num'>{p['policies']}</td>"
                    f"<td class='num'>{_money(p['premium'])}</td><td class='num'>{_money(p['target'])}</td>"
                    f"<td class='num'>{_pct(p['pct_of_target'])}</td>"
                    f"<td><span class='pill {cls}'>{label}</span></td></tr>")
    flags = "".join(f'<div class="flag {f["level"]}"><b>{e(f["title"])}.</b> {e(f["detail"])}</div>'
                    for f in report["flags"] if f["level"] in ("red", "amber"))
    bullets = "".join(f"<li>{e(b)}</li>" for b in brief.get("bullets", []))
    actions = "".join(f"<li>{e(a)}</li>" for a in brief.get("actions", []))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Owner brief {e(report['week'])}</title>
<style>{CSS}</style></head><body>
<div class="top"><div class="agency">{e(agency)} &middot; Weekly owner brief</div>
<div class="week">Week ending {e(week_text)}</div></div>
<h1>{e(brief.get('headline', ''))}</h1>
<div class="kpis">{kpi_html}</div>
<div class="cols"><div><h2>This week</h2><ul>{bullets}</ul></div>
<div><h2>Suggested next steps</h2><ul>{actions}</ul></div></div>
<h2>Producers</h2>
<table><tr><th>Producer</th><th class="num">Policies</th><th class="num">Premium</th><th class="num">Target</th>
<th class="num">% of target</th><th>Status</th></tr>{''.join(rows)}</table>
{f'<h2>Needs attention</h2>{flags}' if flags else ''}
<div class="foot">Numbers calculated by script from {e(report['source']['file'])}
({report['source']['rows_used']} rows used, {report['source']['rows_skipped']} skipped).
Wording drafted by Claude for review. Nothing has been sent.</div>
</body></html>"""


def to_pdf(html_text: str, out: Path) -> bool:
    try:
        from weasyprint import HTML
    except Exception:  # WeasyPrint or its system libraries are not installed
        return False
    HTML(string=html_text).write_pdf(str(out))
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report")
    ap.add_argument("brief")
    ap.add_argument("--out", default="owner_brief.pdf")
    ap.add_argument("--html")
    args = ap.parse_args(argv)
    report = json.loads(Path(args.report).read_text())
    brief, problems = fill_brief(json.loads(Path(args.brief).read_text()), report["metrics"])
    page = render_html(report, brief)
    if args.html:
        Path(args.html).write_text(page)
    if to_pdf(page, Path(args.out)):
        print(f"PDF written to {args.out}")
    else:
        fallback = Path(args.html or Path(args.out).with_suffix(".html"))
        fallback.write_text(page)
        print(f"WeasyPrint not available; HTML written to {fallback} (print it to PDF from a browser)")
    print(f"\nSubject: {brief['email_subject']}\n\n{brief['email_body']}")
    for p in problems:
        print(f"FLAG: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
