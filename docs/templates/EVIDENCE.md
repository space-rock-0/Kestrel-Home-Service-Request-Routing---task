# Evidence

Generated {{trained_at}}. Every number comes from `artifacts/metrics.json`.

## Setup
- Target: the team that finally closed each request, mapped to current team names.
- Split by time. Training rows: {{dev_rows}}. Validation rows: {{val_rows}}. Holdout rows: {{n_holdout}}, starting {{holdout_from}}. The holdout was scored once.
- Closed rows used: {{rows_closed}}. Open rows excluded: {{rows_unclosed}} ({{unclosed_pct}}% of the file).

## Headline (holdout, CRM era)

| | Accuracy vs final team | 95% interval | Macro-F1 |
|---|---|---|---|
| Bot | {{bot_acc_pct}}% | {{bot_ci_lo_pct}}% to {{bot_ci_hi_pct}}% | {{bot_f1}} |
| Model | {{model_acc_pct}}% | {{ci_lo_pct}}% to {{ci_hi_pct}}% | {{model_f1}} |
| Model agreement with the bot's own label | {{agree_pct}}% | | |

Difference: {{delta_pts}} points. Gap between intervals: {{ci_separation_pts}} points.

## How often it is wrong
- Wrong first touch: bot {{wrong_bot_pct}}%, model {{wrong_model_pct}}%.
- Weakest team: {{worst_team}} (recall {{worst_team_recall_pct}}%).
- Text seen in training: {{seen_text_acc_pct}}%. Text never seen: {{unseen_acc_pct}}% ({{unseen_share_pct}}% of holdout).
- First half of holdout months {{first_half_acc_pct}}%, last month {{last_month_acc_pct}}%. Drift {{drift_pts}} points.

## Confidence gate
{{flagged_pct}}% of requests flagged for a person. Accuracy on unflagged {{acc_unflagged_pct}}%. Accuracy on flagged {{acc_flagged_pct}}%.

## Expected score (write this before submitting)
Point {{expected_point_pct}}%, range {{expected_low_pct}}% to {{expected_high_pct}}%.
Method: {{expected_formula}}.

## Error taxonomy (hand-read at least 50 errors from artifacts/errors_holdout.csv)
{{error_taxonomy}}

## Golden cases (python -m kestrel run golden)
{{golden_output}}

## Tried, kept, discarded
{{tried_kept_discarded}}
