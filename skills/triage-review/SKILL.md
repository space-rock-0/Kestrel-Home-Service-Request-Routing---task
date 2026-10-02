---
name: triage-review
description: Review routing errors and decide whether the model is ready to replace the bot.
tools: read_metrics, validate_data, route_request
---

# Triage review

Use when asked whether the router can replace the routing bot.

1. Call `validate_data` with action `train`. Stop and report if `ok` is false.
2. Call `read_metrics`. Compare `holdout.model.accuracy_ci95` with `holdout.bot_vs_final.accuracy_ci95`.
3. Recommend replacement only when the model interval sits above the bot interval by at least 3 points and the flagged share stays under the limit the client set.
4. Read `artifacts/errors_holdout.csv`, group at least 50 errors by cause, and report counts. Use `route_request` to re-check any example you intend to quote.
5. Never quote a number that is not in `metrics.json`.
