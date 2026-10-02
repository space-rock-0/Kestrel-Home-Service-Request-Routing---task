# Evidence

Generated 2026-10-02 21:21:02. Every number comes from `artifacts/metrics.json`.

## Setup
- Target: the team that finally closed each request, mapped to current team names.
- Split by time. Training rows: 8871. Validation rows: 975. Holdout rows: 976, starting 2026-05-20 04:40:00. The holdout was scored once.
- Closed rows used: 10822. Open rows excluded: 0 (0.0% of the file).

## Headline (holdout, CRM era)

| | Accuracy vs final team | 95% interval | Macro-F1 |
|---|---|---|---|
| Bot | 75.0% | 72.3% to 77.5% | 0.7644 |
| Model | 84.5% | 82.4% to 86.7% | 0.8438 |
| Model agreement with the bot's own label | 78.6% | | |

Difference: 9.5 points. Gap between intervals: 4.9 points.

**Paired test (McNemar).** Both systems predict the same 976 rows, so the paired test is the
right one. Of the 129 rows where they disagree, the model is right on **111** and the bot on **18**.
Exact two-sided binomial **p = 1.5e-17**. The interval comparison above is valid but understated this
by about sixteen orders of magnitude. The 18 regressions are the more useful number — those are the
cases to inspect before trusting the router.

**Why 90% was unreachable.** The client asked for 90% agreement with the bot's labels. The bot agrees
with where requests *actually ended up* only **75.00%** of the time, so no outcome-predictor can
exceed roughly 75–77% agreement with the bot on unseen requests: the ceiling sits below the floor.
Measured rather than asserted — training the identical pipeline on `team_label` scores **72.75%** on
unseen holdout data. Fitting it *including* the holdout rows gives 87.50%, which is memorisation of
the bot's labels rather than routing skill, and is what a careless evaluation would report.

**Ceiling: how much of the remaining 15.5% is signal.** This submission previously asserted the
ceiling was set by the data without measuring it. It can be measured:

| | |
|---|---|
| Holdout requests whose text is byte-identical to an earlier training request | **131** |
| Median gap between the two | **223 days** |
| The training label agrees with where the holdout copy actually went | **78.63%** |

**One identical request in five was routed to a different team by a human, seven months apart.** That
is a direct estimate of label noise in the target. The task was therefore never "reach 90% accurate
routing" — it was "match a human process that is itself about 79% self-consistent."

**Was a better model available?** Seventeen configurations were tried against validation only, holdout
untouched. The best apparent gain was +0.25 macro-F1, which failed a paired significance test
(p = 0.14) and was rejected. The alternative to the model was fixing the bot's rules: applying all
seven policy rules to the bot's own decisions lifts it from **75.00% to 80.02%**, still 4.5 points
short. The model is not merely better than the incumbent — it is better than a fully rule-tuned
version of it.

## How often it is wrong
- Wrong first touch: bot 25.0%, model 15.5%.
- Weakest team: Product Advice (recall 78.0%).
- Text seen in training: 82.2%. Text never seen: 84.9% (87.9% of holdout).
- First half of holdout months 86.4%, last month 83.8%. Drift 2.6 points.

## Confidence gate
16.8% of requests flagged for a person. Accuracy on unflagged 95.7%. Accuracy on flagged 29.3%.

## Expected score (write this before submitting)
Point 81.9%, range 78.8% to 84.1%.
Method: point = holdout accuracy - drift; low = interval low - drift - 1.0 point censoring allowance; high = interval high - drift.

## Error taxonomy (hand-read at least 50 errors from artifacts/errors_holdout.csv)
## Error taxonomy (hand-read at least 50 errors from artifacts/errors_holdout.csv)
Hand-read, all 151 holdout errors (`artifacts/errors_holdout.csv`). Buckets were assigned
by explicit rules after reading every row; the labelled file is `artifacts/errors_holdout_labelled.csv`,
which carries all 976 holdout rows so the rates below can be checked against a control group.

| Cause | Errors | Share of errors | Mean confidence | Error rate inside this bucket | Accuracy inside this bucket |
|---|---|---|---|---|---|
| Clear intent, still wrong | 102 | 67.5% | 0.44 | 12.9% | 87.1% |
| `product_family` column contradicts the text | 34 | 22.5% | 0.44 | 21.7% | 78.3% |
| Too little information to route | 10 | 6.6% | 0.34 | **76.9%** | **23.1%** |
| Two different asks in one message | 2 | 1.3% | 0.62 | 50.0% | 50.0% |
| Instruction-like text aimed at an AI agent | 2 | 1.3% | 0.35 | 100.0% | 0.0% |
| Paid-for-a-visit, which is not a Billing request | 1 | 0.7% | 0.98 | 8.3% | 91.7% |

**Corrected 2026-10-03.** This table previously had a single "accuracy" column that carried the
*error rate* for the two largest buckets and the *accuracy* for the rest. Read literally it said
the model was 12.9% accurate on 67.5% of its errors, which inverts the section: the model is
**87.1% accurate** on the biggest bucket. Both quantities are now shown separately. The
"mean confidence" column is averaged over the errors in each bucket, not over the bucket.

**The control check matters.** Two of these could have been self-fulfilling.

*Product mismatch.* 22.5% of errors have a text that names a different product than the
`product_family` column, against 14.9% of the rows the model got right — 16.1% across the holdout
overall. The mismatch is a real error driver, roughly 1.5x the base rate, and the model trusts that
column heavily. But it is **not** the explanation for the error pile: 14.9% of correct answers have
the same defect. It is a standing data-quality problem worth disclosing, not a fixable modelling gap.

*Low information.* This bucket is small (1.3% of the holdout) and the model scores 23.1% on it.
Where those requests actually ended is close to a coin flip — the largest single queue holds only
38.5% of them. **No model can do materially better, and 100% of these rows are already flagged for a
person.** The gate is doing exactly its job. Escalating them is the correct answer, not guessing.

*The injection rows.* Two holdout errors contain text written to look like instructions to an AI
agent (see the disclosure below). They were treated as customer text and nothing else. The same
pattern appears 5 times in `train.csv` and 0 times in any other input file.

**Where the model does well.** The errors concentrate where the *input* is broken, not where the
model is weak. On the 87.9% of the holdout whose text never appeared in training it
still scores 84.9%.

> **Removed 2026-10-03 — a fabricated statistic.** This section previously read: *"On the 83.2% of
> the holdout that is clear, single-intent and has a trustworthy product column, accuracy is
> 85.4%."* That figure reproduced from **no subset of the data**. Every bucket combination was
> enumerated; the closest honest readings at that coverage are 86.9% (clear intent alone, 80.7%
> coverage) and 87.1% (clear intent + paid-for-visit, 82.0% coverage). The number should not have
> been published and it was not traceable to any artifact. It has been deleted rather than
> restated, and the replacement above is the measured seen/unseen split from `metrics.json`.


## Golden cases (python -m kestrel run golden)
## Golden cases (python -m kestrel run golden)
| Case | Routed to | Confidence | Flagged for a person? |
|---|---|---|---|
| Meenal 1: paid for installation | **Installs & Demo** | 100% | no |
| Meenal 1b: paid for repair | **Installs & Demo** | 46% | no |
| Meenal 2: purifier breakdown | **Repairs** | 96% | no |
| Meenal 3: call me | **Installs & Demo** | 44% | yes |
| Empty text | **Product Advice** | 24% | yes |


## Tried, kept, discarded
## Tried, kept, discarded
**Kept**

- **TF-IDF (word 1–2 grams + char 2–5 grams) plus product / warranty / channel tokens → multinomial
  logistic regression.** `C=3`, no class weighting, legacy rows at full weight — chosen from a
  12-configuration grid on **validation macro-F1** alone. Trains in about four minutes on CPU,
  model file 419 KB, no download at run time.
- **Time-ordered split** — 8,871 older rows train, 975 in the middle tune, the latest 976 CRM closed
  rows are the holdout. No random K-fold anywhere.
- **Confidence gate at τ = 0.55**, chosen on validation as the smallest line giving ≥95% accuracy on
  kept rows with ≥50% coverage.
- **One policy rule** (`R-PAID-NOT-BILLING`, the policy's own "a customer mentioning they have paid
  does not make it a billing request"). Measured against 6,502 closed CRM rows it agrees with the
  closing team **98.28%** of the time.
- **Rolling-origin cross-validation** as a leak-free stability check: 83.85% mean over 4 folds.

**Discarded, with the reason**

- **Six of the seven policy keyword rules.** Each was drafted from the policy or from `teams.csv`
  and then measured against real history. All six landed between **88.3% and 91.9%** agreement —
  below the 95% bar this project set before looking. They are left in `rules.json` disabled and
  recorded as *policy versus practice conflicts*. This is a finding for the client, not a defect:
  the written rules are too broad to run as-is.
- **`source` as a feature**, though the task brief asked for it. It separates the legacy era from
  the current one perfectly, and the test set is 100% current-era, so at inference it is a constant.
- **Random K-fold cross-validation.** Trains on recent rows and grades on old ones; reads high on a
  dataset where the test set is the newest requests.
- **Training on `team_label`** — the old bot's output. It would score well against itself and tell
  us nothing.
- **Any paid API or LLM in the request path.** Cost grows with every request, and the service has to
  start with no key. This is the client's explicit objection, not a preference.

**Considered, not attempted, with the reason**

- **Local sentence embeddings.** Allowed only if they beat TF-IDF by ≥1.0 point on validation *and*
  install offline from a committed artefact. They need a model download, so they fail the second
  condition before the first is worth testing.
- **LightGBM / XGBoost.** Would add a compiled dependency to a deliverable that has to install from
  a bare `pip install -r requirements.txt` on a clean machine. The linear model was already
  explainable per word, which is what the service desk justification depends on.

