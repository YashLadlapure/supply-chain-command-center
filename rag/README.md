# Ask the data

A question-answering tool for the supply-chain database. You type a plain-English question ("What was OTIF for North region warehouses?"). It finds the relevant notes about the tables and KPIs, writes one read-only SQL query, runs it, and returns the number together with the SQL it used.

**Status:** in progress. The scope, the targets and the knowledge cards are written. Nothing runs yet, and there are no scores yet.

## What it answers

- KPI values, with optional filters: region, warehouse, product category, supplier and month. Examples: OTIF %, fill rate, inventory value, lead time, forecast accuracy, supplier score.
- Counts, such as open orders, low-stock locations or late purchase orders.
- Top-N and bottom-N lists, such as the 5 suppliers with the lowest on-time rate.
- "What does X mean" questions about a KPI, a table or a status value.

## What it does not do

- Change data. Every query is a single `SELECT`, run by a database user that cannot write.
- Forecast the future or give advice. It reports what is in the data.
- Answer about data the project doesn't have: defects, customer satisfaction, costs, employees, or any year other than 2025. For these it replies "not available in this data" instead of guessing.

## Targets

These were fixed before any code was written, so the results can't be bent to fit them.

| Target | Pass mark |
|---|---|
| Validated KPI slices answered correctly (from [`docs/validation-log.md`](../docs/validation-log.md)) | at least 15 of 18 |
| Questions about missing data correctly refused | at least 4 of 5 |
| Unsafe SQL executed (anything other than one read-only `SELECT`) | never |
| Average time to answer | under 10 seconds |

## Knowledge cards

The tool can only be as accurate as its notes. Each note is a short Markdown section that starts with a `##` heading and covers one thing.

| File | What the cards cover |
|---|---|
| [`knowledge/tables.md`](knowledge/tables.md) | the 9 tables and 3 views: columns, keys, status values, pitfalls |
| [`knowledge/kpis.md`](knowledge/kpis.md) | each KPI: meaning, formula, grain, filters that do and don't apply |
| [`knowledge/rules.md`](knowledge/rules.md) | business rules and data limits, such as the snapshot date |
| [`knowledge/examples.md`](knowledge/examples.md) | example questions with the SQL that answers them, taken from `sql/queries/` |

The cards hold definitions and SQL only, never the answers. The reference values live in the validation log, and the test questions are scored against them.
