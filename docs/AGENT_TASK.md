# AGENT_TASK.md

The job for an AI coding agent. Read `AGENTS.md` for code rules first. This file says what to do, in what order, and when to stop.

## Mission

The user has real Excel files for the Kestrel Home routing assignment. Run the pipeline on them, read what the data says, and produce the assignment's written outputs with measured numbers. The code is finished. Your work is data work, judgement, and honest reporting.

## Stop and ask the user if

- `data/input/` has no files. Do not create data. Do not use `tests/synth.py` output as results.
- `python -m kestrel doctor` shows a FAIL you cannot fix by following its message.
- A required column is missing and no alias fits. Report the exact file and column.
- The policy PDF has no cost for one transfer. Leave the rupee saving unquantified and say so.
- Two files match one role and you cannot tell which is right.

## Order of work

Run every command from the project root. Each gate must pass before the next step.

| # | Command | Gate to continue |
|---|---|---|
| 1 | `python -m kestrel doctor` | No FAIL |
| 2 | `python -m kestrel status` | Roles found: train, resolution, teams (test and sample_submission if supplied) |
| 3 | `python -m kestrel run policy_text` | Read `artifacts/policy.txt`. Write down the transfer cost with its page, team renames, system change dates |
| 4 | `python -m kestrel validate` | `ok: true`. Read every warning and note it in `NOTES.md` |
| 5 | `python -m kestrel audit` | Read `artifacts/audit.txt` fully. Answer the Phase 1 questions in `docs/BUILD.md` |
| 6 | `python -m kestrel run full_pipeline` | Job succeeds, `predictions.csv` check passes |
| 7 | `python -m kestrel run golden` | Read the five cases. Report any that look wrong |
| 8 | `python -m kestrel run audit_rules` | Enable a rule in `rules.json` only when `recommend_enable` is true |
| 9 | Read `artifacts/errors_holdout.csv` | Hand-label at least 50 errors into causes. Count them |
| 10 | `python -m kestrel run form_values` | Writes `artifacts/form_values.json` |
| 11 | `python -m kestrel run render_docs --transfer-cost-inr N --hosting-inr-month M` | N from the policy PDF. M from the user, 0 if none |
| 12 | Fill every placeholder left in `output/MEMO.md` and `output/EVIDENCE.md` | No `{{...}}` remains |
| 13 | Fill `docs/submission-form.md` from `artifacts/` | No `⟦…⟧` remains |
| 14 | `python -m kestrel doctor --strict` and `pytest -q` | All pass |

If you re-run training after step 9, repeat steps 7 to 14.

## Rules about numbers

- Every number in a deliverable comes from `artifacts/metrics.json`, `artifacts/form_values.json`, `artifacts/audit.txt`, the policy PDF, or the user. Cite which.
- Never round up, estimate by feel, or reuse a number from a synthetic test.
- The expected-score estimate in the form is written before the real score exists. Do not edit it afterwards.
- If the model is not better than the bot, say so. Decision B in the memo is a valid, honest outcome.

## Do not

- Train on `team_label`. It is the old bot's output.
- Add `source`, `resolved_at`, `transfers` or `first_team` as features.
- Tune on the holdout, or look at holdout errors before step 6.
- Add a paid API call to the request path.
- Delete or rewrite `data/input/` files.
- Extract code from `docs/BUILD.md`. Its code blocks are superseded by `kestrel/`.
- Mark a task done without running its command and reading the output.

## What the agent cannot do

These need the human. List them in your final report as open items.

| Item | Why |
|---|---|
| Screen recording (at most 3 minutes) | Needs a person on screen |
| Google Drive upload and public link | Needs the user's account |
| GitHub repository creation and push | Needs the user's account |
| Honest hours spent | Only the user knows |
| What AI tools were used and what they cost | Only the user knows |
| Hosting price | Depends on the user's infrastructure |
| Deciding between memo option A and B | The rule gives a suggestion. The user owns the call |

## Final report format

Send the user:

1. What was run, with the exit status of each command in the table.
2. The headline numbers and where each came from.
3. Anything surprising in the audit. Anything that failed. Anything you did not do.
4. The open items from the table above.

Keep it short. Do not claim success on anything you did not verify.

## Failure table

| Symptom | Likely cause | Action |
|---|---|---|
| `missing_file` | File name and headers match no role | Rename the file to the role name, or add aliases in `config/datasets.json` |
| `missing_columns` | Header differs from the schema | Add an alias in `config/datasets.json`, re-run `validate` |
| `bad_timestamps` | Dates stored as text in an odd format | Report sample values to the user. Do not guess the format |
| `Only N closed 'crm' requests` | Few rows have a final team, or `source` values differ | Check `audit.txt` source counts. Report to the user |
| Model accuracy below bot | Data or labels are weak | Say so. Use memo option B |
| Teams never seen as final team (warning in job log) | A team name changed or is rare | Check the rename map in `audit.txt`. Report |
| Everything flagged for a person | Confidence line too high for this data | Report `gate_from_validation`. Do not lower the line to hide it |
