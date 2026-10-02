# Input folder: put your Excel files here

This folder is empty on purpose. The project ships no data.

Copy your files in. The app finds them on its own, either at the next scan (every 5 seconds while the server runs) or on the next command.

## Files the app looks for

| Role | File name (any of) | Required columns |
|---|---|---|
| train | `train.xlsx` | request_id, created_at_ist, channel, product_family, warranty_status, request_text, source, team_label |
| test | `test_unlabelled.xlsx`, `test.xlsx` | same as train, without team_label |
| resolution | `resolution_log.xlsx` | request_id, first_team, final_team, transfers, resolved_at |
| teams | `teams.xlsx` | team, renamed_to, handles |
| sample_submission | `sample_submission.xlsx` | request_id, team (optional file) |

## Rules

- `.xlsx`, `.xlsm`, `.xls`, `.csv` and `.tsv` all work. You can mix formats.
- A file is matched by its name first. If the name does not match, its column headers decide. `export_final.xlsx` with train columns is treated as train.
- Header text is normalised: `Request ID` and `request_id` are the same column.
- With several sheets, the sheet named after the role is used (`Train`, `Teams`), else the first sheet. Set `KESTREL_EXCEL_SHEET` to force one.
- Two files for one role: the newest wins, and the app warns you.
- Files starting with `~$` (Excel lock files) and hidden files are ignored.
- Alternative header names are mapped for you (`Ticket ID` to `request_id`, `Created At` to `created_at_ist`, `Bot Queue` to `team_label`, and more). The Input data tab shows each mapping. Add your own in `config/datasets.json` under `aliases`.
- Dates can be real Excel dates, text, or raw Excel serial numbers (a date cell formatted as General). All three parse.
- Put `ops-policy.pdf` here too. It is not a data file, so discovery ignores it. `python -m kestrel run policy_text` reads it.
- To change required columns or file names, edit `config/datasets.json`.

Nothing else is needed. Open the **Input data** tab in the web app to see what was detected.
