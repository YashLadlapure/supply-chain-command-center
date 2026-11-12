# Evaluating "Ask the data"

This measures how well the [`rag/`](../rag) question-answering tool turns plain-English
questions into correct, read-only SQL answers, and whether the knowledge cards make a
difference. The targets were fixed in [`rag/README.md`](../rag/README.md) before any
answering code was written, so the results cannot be bent to fit them.

## The two setups

Every question is run twice, so the cards can be measured against a fair baseline:

- **Baseline** — the model sees only the database schema (`sql/schema.sql`).
- **Retrieval** — the model also sees the knowledge cards that the card search returns for the question.

Everything else is identical: the same model (`qwen2.5:7b`, run locally with Ollama), the
same SQL guard, and the same read-only database user.

## The question set

35 questions, in [`rag/eval/questions.yaml`](../rag/eval/questions.yaml):

- **18 validated KPI slices** — their correct values come from [`docs/validation-log.md`](validation-log.md), where SQL and Power BI agree.
- **12 extra questions** — counts, values and top/bottom-N lists, each answer produced by running SQL against the seed data.
- **5 that must be refused** — the data cannot answer them (defects, customer satisfaction, costs, staffing, a year outside the snapshot).

Each question is scored by its type:

- `value` — correct when the answer returns a number within `tolerance` of the expected value.
- `list` — correct when it returns exactly the expected names, in the expected order.
- `refuse` — correct when the tool refuses, because the data cannot cover it.

## Results

| Setup | Answerable (of 30) | Refusals (of 5) | Avg time |
|---|---|---|---|
| Baseline (schema only) | 6 | 4 | 4.9 s |
| Retrieval (schema + cards) | **20** | **5** | 7.5 s |

The card search returned all of the expected cards for 34 of the 35 questions.

Against the fixed targets:

| Target | Pass mark | Result |
|---|---|---|
| Validated KPI slices answered correctly | at least 15 of 18 | 10 of 18 — **not met** |
| Questions about missing data correctly refused | at least 4 of 5 | 5 of 5 — met |
| Unsafe SQL executed | never | never — met |
| Average time to answer | under 10 seconds | 7.5 s — met |

## What the numbers say

The cards more than triple the answerable score, from 6 to 20 out of 30, and lift refusals
from 4 to a clean 5 out of 5. The schema alone is not enough: without the KPI formulas and
business rules, the model guesses the grain and the filters and gets most slices wrong.

The accuracy target is still missed. The limit is the local model's SQL on the harder KPIs,
not the card search, which found the right cards for 34 of 35 questions.

## The 10 remaining misses

They fall into two groups.

**Invalid SQL, so the tool refused (6).** The model wrote SQL the guard or the database
rejected, on both the first try and the retry, so the tool refused rather than return a wrong
number:

- OTIF overall, OTIF North, OTIF June — nested aggregate functions (`AVG(... MAX(...) ...)`), which PostgreSQL does not allow.
- Supplier score for one supplier — the model referenced a table that does not exist (`supplier_stats`); the guard rejected the unknown table.
- West region actual lead time — a join the model built incorrectly.
- Low-stock count — it referenced `products` without joining it.

This is the safety layer working as intended: when the model cannot write valid SQL, the tool
refuses. It does not return a wrong number for these.

**Valid SQL, wrong formula (4).** Here the SQL ran, but the logic was wrong, so the tool
returned a wrong number:

- Forecast accuracy overall and for June — the model averaged per-row percentage error instead of using the weighted formula from the KPI card; one of the two produced a nonsense value.
- Planned lead time — the model filtered the wrong rows.
- Bottom-3 suppliers by on-time rate — the right suppliers, but in the wrong order.

The safety layer does not catch these, because the SQL is valid; only the business logic is
wrong. Closing this gap is the next step.

## Next step

The failures are concentrated in a few KPIs that need a multi-table query or a specific
formula. The plan is to add canonical worked-SQL example cards for exactly those KPIs (OTIF,
forecast accuracy, supplier score, low-stock count), drawn from the queries in `sql/queries/`,
and re-run this evaluation. A stronger model would also help, but the larger local models
tested did not fit the available GPU, so the small model stays and the cards carry the work.

## Reproducing this

With the database running, the card index built, and Ollama serving the models:

```
python rag/eval/run_eval.py
```

It writes per-question results and a summary to [`rag/eval/results/`](../rag/eval/results).
The run is deterministic (`temperature` 0), so the numbers above reproduce.
