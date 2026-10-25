# Spreadsheet columns

The script finds the header row itself, so title rows above it are fine. Column names are matched without regard to case, spaces or punctuation.

## Sheet: Production
| Column | Meaning | Example |
|---|---|---|
| Date | Date the policy was written | 10/21/2026 |
| Producer | Producer's name, as in the Targets sheet | Maya Chen |
| Policy Number | Carrier policy number | AU-482913 |
| Customer | Customer name | Maria Lopez |
| Line | Auto, Home, Commercial or Life | Auto |
| Business Type | New or Renewal | New |
| Written Premium | Annual premium written, number or text such as "$1,250.00" | 1250.00 |

A row whose producer is "TOTAL" is ignored; the script computes its own totals.

## Sheet: Renewals Due
| Column | Meaning |
|---|---|
| Producer | Producer's name |
| Policy Number | Policy up for renewal this week |
| Line | Auto, Home, Commercial or Life |
| Expiring Premium | Premium on the policy that is expiring |
| Outcome | Renewed or Lost |

Retention = renewals kept / renewals due, counted by policy.

## Sheet: Targets
| Column | Meaning |
|---|---|
| Producer | Producer's name |
| Weekly Premium Target | Weekly written premium target in dollars |

## Mapping a real export
If your system uses other names (for example "Agent" instead of "Producer"), add them to the `PRODUCTION_COLS`, `RENEWAL_COLS` or `TARGET_COLS` maps at the top of `scripts/compute_report.py`.
