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
| Baseline (schema only) | 7 | 4 | 5.3 s |
| Retrieval (schema + cards) | **26** | **5** | 6.8 s |

The card search returned all of the expected cards for 32 of the 35 questions.

Against the fixed targets:

| Target | Pass mark | Result |
|---|---|---|
| Validated KPI slices answered correctly | at least 15 of 18 | 16 of 18 — met |
| Questions about missing data correctly refused | at least 4 of 5 | 5 of 5 — met |
| Unsafe SQL executed | never | never — met |
| Average time to answer | under 10 seconds | 6.8 s — met |

## What the numbers say

The cards nearly quadruple the answerable score, from 7 to 26 out of 30, and lift refusals
from 4 to a clean 5 out of 5. The schema alone is not enough: without the KPI formulas and
business rules, the model guesses the grain and the filters and gets most slices wrong.

The jump from an earlier run (20 of 30) came from adding worked-SQL example cards for the KPIs
the model kept getting wrong. The clearest case was forecast accuracy: the model divided two
integer columns, so PostgreSQL did integer division and the accuracy came out near 100%. A
worked example that forces the division to run on decimals fixed every forecast-accuracy
question. Other examples gave the full query for OTIF, supplier score and the lead-time and
low-stock counts, which the model then followed instead of inventing a broken one.

## The 4 remaining misses

- **Inventory value, overall** — the model wrote SQL the guard or the database rejected on both tries, so the tool refused rather than return a wrong number.
- **Inventory value, Electrical** — the SQL ran but a join multiplied rows, so the total came out far too large. The SQL is valid, only the logic is wrong, so the safety layer does not catch it.
- **Stockout risk count** — the model's query failed on both tries and the tool refused. This one needs a windowed demand calculation that the small model does not write reliably.
- **Bottom-3 suppliers by on-time rate** — the right suppliers, but in the wrong order.

Three of the four are the same pattern as before: when the model cannot write valid SQL, the
tool refuses instead of guessing. Only the Electrical inventory-value answer returns a wrong
number, and only because its SQL is valid while its join is wrong.

## Next step

The remaining misses are concentrated in inventory value and stockout risk, both of which need
a multi-table or windowed query. The same fix that worked for the others applies: add a
worked-SQL example card for each, drawn from the queries in `sql/queries/`, and re-run this
evaluation. A stronger model would also help, but the larger local models tested did not fit
the available GPU, so the small model stays and the cards carry the work.

## Reproducing this

With the database running, the card index built, and Ollama serving the models:

```
python rag/eval/run_eval.py
```

It writes per-question results and a summary to [`rag/eval/results/`](../rag/eval/results).
The run is deterministic (`temperature` 0), so the numbers above reproduce.
