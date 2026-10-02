# NOTES.md — what the data says

Findings only. **No choices are recorded here** — those go in `decisions.md`.
Every number below comes from a real command's output, with the file it came
from. Blank means not yet measured; it does not mean zero.

This file is required by `docs/AGENT_TASK.md` steps 4 and 5 and checked by
`docs/BUILD.md` §13 ("Audit read; NOTES.md answers all Phase 1 questions").

---

## Sources

| Tag | File | Produced by |
|---|---|---|
| A | `artifacts/audit.txt` | `python -m kestrel run audit` |
| M | `artifacts/metrics.json` | `python -m kestrel train` |
| C | `artifacts/confusion_holdout.csv` | training |
| G | `python -m kestrel run golden` | fixed cases from the client's email |
| P | `data/input/ops-policy.pdf` | read by eye — **cite the page** |
| H | `hours.log` | human |

*(A "probe" tag means a read-only pandas check of `data/input/` run before the
official command. Where both exist they agree exactly — the probe was kept only
as an early-warning pass, never as the source of a published figure.)*

---

## Which world are we in?  ✅ ANSWERED

`docs/BUILD.md` Phase 4 gate: compare baseline B1 (the bot's own label scored
against `final_team`) to the model.

- If **B1 ≥ 90%** vs `final_team` → the bot is roughly right; this is a
  "replace it cheaply" story (licence saving).
- If **B1 is far lower** → this is a "fix routing" story (transfer saving).

> **Answer: the "fix routing" world.**
>
> *(M)* Holdout, the same 976 most recent CRM requests:
>
> | | Accuracy vs `final_team` | 95% interval | Macro-F1 |
> |---|---|---|---|
> | Bot (incumbent) | **75.00%** | 72.33% – 77.46% | 76.44% |
> | This model | **84.53%** | 82.38% – 86.68% | 84.38% |
>
> The bot is right fewer than 4 times in 5. It is nowhere near 90%, and the whole
> framing is therefore **wasted transfers**, not just licence money. The model
> is **+9.53 points** better and the two intervals **do not overlap** — the gap
> between them is **4.92 points**, so the win is distinguishable and not noise
> (`docs/BUILD.md` §7 requires this explicitly before a win may be claimed).
>
> The memo decision rule needs one input the data cannot supply: the share of
> requests the client is willing to send to a person. Measured flagged share is
> **16.8%**. That limit is the user's call — see `decisions.md` D11.

---

## Phase 1 questions (`docs/BUILD.md`)

### 1. Does `created_at_ist` parse?  ✅ ANSWERED
- *(A)* **unparsed train rows: 0.** No `dayfirst` fallback was needed.
- *(A)* train date range: **2025-04-01 00:31 → 2026-06-30 23:33**

### 2. Legacy Zoho vs CRM  ✅ ANSWERED
- *(A)* train by source: `crm` **6,502**, `legacy_zoho` **4,320**
- *(A)* test range: **2026-07-01 →**, 2,178 rows — **entirely post-cutover, 100% CRM**
- *(A)* test vs last-60-days-of-train match is close on all three categoricals
  (largest gap `ivr` 30.3% test vs 27.7% train). **No material distribution
  shift** — this supports the expected-score estimate.

### 3. Mojibake rate by source, before and after cleaning  ✅ ANSWERED
- *(A)* raw by source: `crm` **0.000000**, `legacy_zoho` **0.111111**
- *(A)* after cleaning: **0.0**
- rows still unreadable: **0**

**Interpretation.** Confined entirely to the legacy Zoho export, absent from the
CRM era. `clean_text` (`ftfy` + NFKC + lowercase) repairs all of it. Because the
test set is 100% CRM-era this cannot affect test predictions — it matters only
for training rows, and is repaired before the vectoriser sees them.

### 4. Empty `request_text` rate by channel  ✅ ANSWERED
- *(A)* `chat` **0.0**, `email` **0.0**, `ivr` **0.0**, `whatsapp` **0.0**

**No empty request text anywhere.** The plan expected blank IVR transcripts. They
are not blank. So the "no information" problem in this dataset is *vague* text
("please call me about my purifier"), not *absent* text — which is exactly what
the confidence gate has to catch. The empty-text path still exists for live
traffic and is exercised by the golden cases.

### 5. Closed rate by month  ✅ ANSWERED — no censoring at all
- *(A)* **every month is 1.0**, 2025-04 through 2026-06
- *(M)* `rows_unclosed: 0`

**This does not match trap T6.** The plan assumed the newest rows would still be
open and would bias the holdout toward easy tickets. They are not. Therefore:

- **no censoring haircut** is needed in the expected-score estimate
- **no bot-label fallback** is needed for D6
- the 15/15 split holds with room to spare (6,502 CRM closed vs the 400 gate)

### 6. Bot-vs-final agreement  ✅ ANSWERED
- *(A)* all 10,822 closed rows: **77.17%**
- by month: 2025-04 **79.3%** → 2026-06 **74.1%** — a slow decline, so the bot is
  getting slightly worse over time, not better
- *(M)* holdout: **75.00%**, CI **[72.33, 77.46]**

### 7. Bot team × final team crosstab  ✅ ANSWERED — Meenal's complaints, quantified
*(A)* rows = where the bot sent it, columns = where it actually ended.

| Bot sent to | total | stayed | **left the queue** | share that left |
|---|---|---|---|---|
| Repairs | 3,129 | 1,993 | **1,136** | **36.3%** |
| Billing | 1,656 | 1,071 | **585** | **35.3%** |
| Filters & Consumables | 1,458 | 872 | **586** | **40.2%** |
| Installs & Demo | 1,186 | 1,146 | 40 | 3.4% |
| Product Advice | 1,180 | 1,135 | 45 | 3.8% |
| Returns & Replacement | 1,174 | 1,132 | 42 | 3.6% |
| Warranty Claims | 1,040 | 1,002 | 38 | 3.7% |

The two leaks named in the email thread, with counts:

- **Billing ← "paid for installation/repair"**: **146** requests the bot sent to
  Billing ended at **Installs & Demo**
- **Filters & Consumables ← "purifier breakdown"**: **315** requests the bot sent
  to Consumables ended at **Repairs**

Billing and Consumables are the **only** queues with a materially wrong routing
rate (35–40%); the other five sit at 3–4%. That is a precise, actionable finding
for Meenal, and it stands on its own whether or not the model ever ships.

### 8. `resolved_at` for Zoho rows  ✅ ANSWERED — broken, and correctly unused
- *(A)* `legacy_zoho`: **1,140 rows with negative durations**, min **−5.0 h**;
  median 4.0 h against CRM's 9.5 h
- *(A)* `crm`: **0 negative durations**

**What is wrong:** the legacy export's resolution clock is offset, so some requests
appear to close before they were created. **Not fixed, deliberately** — it is not a
model feature anywhere, and `AGENTS.md` bans `resolved_at` as one. Recorded as a
data limitation for `submission-form.md` Q5.

### 9. Exact-duplicate texts, train ↔ test  ✅ ANSWERED
- *(A)* **258 of 2,178** test rows (11.8%) have text that also appears in train
- *(M)* holdout: **87.91%** of scored rows have text never seen in training
- *(M)* accuracy: seen text **82.20%**, unseen text **84.85%**

**Unseen text scores slightly *higher*** — the opposite of the usual
template-overfit pattern. So the conservative bound for this model is the
**unseen-text figure (84.85%)**, not the headline. With the good distribution
match in Q2, that is evidence it generalises rather than memorises. Kept per
BUILD.md D7.

### 10. Team names outside the canonical set  ✅ ANSWERED
- *(A)* **none.** `final_team` resolves to exactly the 7 official queues.
- *(A)* the rename map confirms 9 surface spellings collapse to 7 canonical names
- before the Phase 1 fix: 2 stray values, 15.5% of rows — `errors.md` E4

---

## Team naming — verified from `data/input/teams.csv`

The seven teams, and the two that were renamed on 15 Jan 2026:

| team | renamed_to | handles |
|---|---|---|
| Installations | `Installs & Demo (from 15 Jan 2026)` | New-product installation, demo and wall-mounting visits. |
| Repairs | — | Product faults, breakdowns, error codes, noise, leaks — needs a technician. |
| Consumables | `Filters & Consumables (from 15 Jan 2026)` | Filters, candles, membranes, jars, brushes, blades, AMC kits. **Not faults.** |
| Billing | — | Invoices, GST, double charges, refunds, EMI conversion, coupons. **Only when the problem IS the payment.** |
| Returns & Replacement | — | Damaged, wrong or incomplete deliveries; returns and exchanges in window. |
| Warranty Claims | — | Warranty and Kestrel Shield registration, coverage, claim status. |
| Product Advice | — | Pre- and post-purchase usage questions. **No fault reported.** |

**`decisions.md` D5 — RESOLVED.** The `renamed_to` values carry a date suffix.
✅ **Confirmed on the real data and fixed.** The canonical set the audit produced
*(A)* is exactly these seven, with no date in any name:

```
['Billing', 'Filters & Consumables', 'Installs & Demo',
 'Product Advice', 'Repairs', 'Returns & Replacement', 'Warranty Claims']
```

The rename is real and complete — the old spellings stop and the new ones start:

| team | old spelling rows | new spelling rows | last month old name appears |
|---|---|---|---|
| Installations → **Installs & Demo** | 745 | 440 | 2026-01 (partial month, 27 rows) |
| Consumables → **Filters & Consumables** | 927 | 531 | 2026-01 (partial month, 40 rows) |

In the **last 60 days of training data** the old spellings do not appear at all
(`Installations` 0, `Consumables` 0) while the new ones do (`Installs & Demo` 145,
`Filters & Consumables` 202). The test set begins 2026-07-01, entirely after the
15 Jan 2026 rename, so the **new** names are the correct output naming — and
`artifacts/predictions.csv` uses them.

> ⚠️ **`sample_submission.csv` cannot answer this question.** All 2,178 of its
> rows contain the single placeholder value `Repairs`. It is a template, not a
> sample. `docs/BUILD.md` T3 and `docs/AGENT_TASK.md` both say to settle naming
> against this file; that instruction cannot be followed on this dataset. Logged
> as `errors.md` E5. Resolved from date evidence instead.

---

## Phase 2 results — model, holdout, gate  ✅ MEASURED

*(M) `artifacts/metrics.json`*

### Setup

| | |
|---|---|
| Training rows (all closed) | dev **8,871** · validation **975** · holdout **976** |
| Validation from | 2026-04-08 |
| Holdout from | 2026-05-20 |
| Closed rows used | **10,822** · unclosed excluded: **0** |
| Model | TF-IDF word 1–2 + char 2–5 + categorical tokens → Logistic Regression |
| Chosen on validation macro-F1 | `C=3`, `class_weight=None`, `zoho_weight=1.0` (12-config grid) |
| Validation (selection) | accuracy **85.95%**, macro-F1 **85.75%** |
| Cost per prediction | **₹0** — no paid API anywhere in the request path |

### Headline (holdout, CRM era, latest 15%, scored once)

| | Accuracy vs `final_team` | 95% interval | Macro-F1 |
|---|---|---|---|
| Bot (incumbent) | **75.00%** | 72.33% – 77.46% | 76.44% |
| This model | **84.53%** | 82.38% – 86.68% | 84.38% |
| Model agreement with the bot's own label | 78.59% | — | 79.64% |

- **difference: +9.53 points**; gap between the intervals: **4.92 points** — they
  do not overlap, so the improvement is distinguishable from noise
- **wrong first touch:** bot **25.00%**, model **15.47%** → a **9.53 point** drop
  in wasted hand-offs, which is the quantity the rupee model multiplies by volume

### The confidence gate works

| | |
|---|---|
| Confidence line (chosen on validation) | **τ = 0.55** |
| Share flagged for a person, holdout | **16.80%** |
| Accuracy on rows **not** flagged | **95.69%** |
| Accuracy on rows **flagged** | **29.27%** |

The flagged pile really is the ambiguous pile — 29.27% is close to what guessing
would give across 7 queues. This is the evidence that lets the memo recommend
auto-routing the confident 83% and asking one question on the rest.

### Robustness

| Check | Value | Reading |
|---|---|---|
| **Rolling-origin CV, 4 forward-chaining folds** | **83.85%** mean, range 82.06%–85.15% | leak-free CV |
| Text seen in training | 82.20% | slightly **lower** |
| Text never seen in training | **84.85%** (87.91% of holdout) | generalises |
| Accuracy by month | 2026-05 **86.40%**, 2026-06 **83.81%** | drift **−2.59 pts** |
| Average transfers logged on holdout | 0.38 | — |

The rolling-origin CV is the honest answer to "cross-validation accuracy". It
walks forward through time — each fold trains on every row older than its own test
slice — so no fold ever grades the model on rows it was trained alongside. It runs
**only on training rows**; validation and holdout are untouched. Random K-fold is
not used anywhere in this project (`docs/BUILD.md` T5, `decisions.md` D10).

| fold | trained on | scored on | accuracy |
|---|---|---|---|
| 1 | 4,320 rows | 2025-10-01 → 2025-11-18 | 82.06% |
| 2 | 5,457 rows | 2025-11-18 → 2026-01-03 | 85.06% |
| 3 | 6,595 rows | 2026-01-03 → 2026-02-22 | 83.13% |
| 4 | 7,733 rows | 2026-02-22 → 2026-04-08 | 85.15% |

The CV mean (83.85%) and the single holdout score (84.53%) agree closely, which is
what you want to see: the holdout is neither a lucky nor an unlucky slice.

The mild downward month-on-month drift is the one signal arguing for a haircut on
the expected score (see Q2's favourable distribution match, which argues the other
way). Both belong in the expected-score statement, written **before** submission.

### Model is frozen

The model configuration was selected on **validation** before the holdout was
touched, and has not changed since. Proof, from a byte-level comparison of
`metrics.json` before and after the CV diagnostic was added: the only fields that
differ are `cv_rolling` (new) and `trained_at` (timestamp). `split`,
`chosen_params`, `validation`, `gate_from_validation`, `holdout`,
`per_class_holdout` and `test` are **identical**, and `predictions.csv` is
byte-for-byte the same file. No number was tuned on the holdout — `decisions.md`
D5 and D11.

### Golden cases — the client's own complaints  ✅ 3 clean wins, 2 correctly flagged

*(G) `python -m kestrel run golden`*

| Case | Routed to | Confidence | Flagged | vs old bot |
|---|---|---|---|---|
| "I paid for the installation but nobody has come yet" | **Installs & Demo** | **99.8%** | no | bot said Billing — **fixed** |
| "I already paid for the repair visit, please send the technician" | Installs & Demo | 46.0% | **yes** | ambiguous — correctly escalated |
| "my water purifier stopped working and is leaking" | **Repairs** | **95.6%** | no | bot said Consumables — **fixed** |
| "please call me about my purifier" | Installs & Demo | 43.6% | **yes** | unroutable — correctly escalated |
| *(empty text)* | Product Advice | 24.1% | **yes** | no information — correctly escalated |

Both leaks Meenal named are fixed with high confidence. The three genuinely
ambiguous inputs are all below the line and escalated rather than guessed. The
second case is arguably better handled by Repairs than Installs & Demo — the
model is honest about not knowing, which is the behaviour we want.

### Submission file

*(A/C/M)* `artifacts/predictions.csv` — **2,178 rows**, columns exactly
`request_id,team`, matching `sample_submission.csv`. 0 blank cells, 0 nulls,
0 duplicate ids, id set identical to the test file, all 7 values inside the
canonical set. `python -m kestrel check` returns `ok: true` with no errors and
no warnings.

Distribution: Repairs 567 · Installs & Demo 314 · Returns & Replacement 300 ·
Warranty Claims 272 · Product Advice 269 · Billing 259 · Filters & Consumables 197.
Flagged for a human: **15.47%**.

---

## Closed CRM rows — training gate headroom

*(A)* **6,502** rows are both closed and `source == crm`.

- `train.py` gate `MIN_CLOSED_CRM = 200` → passes with large headroom
- `docs/BUILD.md` Phase 3 gate: ≥ 400 CRM closed rows for the 15/15 split →
  passes, so **no fallback to the 10/10 split**

---

## From the ops-policy.pdf — with page references

**Required before any rupee figure exists.** `docs/AGENT_TASK.md` step 3. If the
PDF has no cost for one transfer, the saving stays unquantified and we say so.

| What | Found? | Page / section | Value |
|---|---|---|---|
| Cost per transfer | _pending_ | | |
| Cost per misroute / call | _pending_ | | |
| Routing rules (warranty, product, channel) | _pending_ | | |
| Team changes (renames, merges, new teams) | _pending_ | | |
| Zoho → CRM cutover date | _pending_ | | |
| Anything about the bot itself | _pending_ | | |

- `policy.txt` written: _pending (`kestrel run policy_text`)_
- PDF is text or scanned: _pending_

---

## PII scan (`docs/BUILD.md` T12)

Grep `data/input/*.csv` for `\b\d{10}\b`, `@`, `+91`.

- 10-digit numbers: _pending formal scan_
- emails: _pending formal scan_
- names: _pending formal scan_
- **Disclosure decision** — commit as supplied, or mask in the committed copy?
  Depends on whether the brief permits masking. _pending — user's call_

> **Observation from the Phase 1 probe (not a scan).** The request texts contain
> identifiers of the form `reg no SR75294` (customer registration numbers) and
> `order KO2608005` (order numbers), e.g.
> `"sir how to clean robot vacuum reg no SR75294"`. These look like internal
> reference numbers rather than direct personal identifiers — no names, phone
> numbers or email addresses were visible in the sample rows read. **Do not treat
> this as the answer**: the formal scan has not been run, and a `reg no` that maps
> 1:1 to a customer is still personal data under most regimes. This decides
> whether the committed copy gets masked (`decisions.md` D6).

---

## Validation warnings (`docs/AGENT_TASK.md` step 4)

Every warning `kestrel validate` reports gets a line here, even the harmless
ones. Silently-accepted warnings are how real problems get missed.

- *(A)* `kestrel doctor` reported `validation: 0 warning(s)`
- `kestrel validate` run standalone: _pending explicit confirmation_
- the loader's `unknown_team_names` check: **no issues** — every label is one of
  the 7 canonical queues after the Phase 1 fix

---

## Data limitations to disclose in `docs/submission-form.md` Q5

Fill only what the audit confirmed. Each needs a number.

- [x] ~~Closed rate drops in recent months (censoring)~~ — **does not apply.** Every
      month is 1.0; `rows_unclosed: 0`. Disclose as "no censoring in this dataset".
- [x] Zoho mojibake, rows still unrecoverable — **11.111% of legacy Zoho rows,
      0% of CRM, 0 rows unrecoverable after cleaning**
- [x] Zoho `resolved_at` unusable — **1,140 rows with negative durations, min
      −5.0 h; CRM has none; not used as a feature**
- [x] `source` excluded as a feature — **perfectly separates `crm` / `legacy_zoho`;
      test set is 100% CRM so it would be constant at inference**
- [x] Teams renamed — **Installations→Installs & Demo, Consumables→Filters &
      Consumables, 15 Jan 2026; 9 spellings collapsed to 7**
- [ ] PII found: how much, and how handled — _pending formal scan_
- [x] Exact-duplicate texts — **258 of 2,178 test rows (11.8%)**
- [x] No customer ID, so repeat customers can straddle the split — **accuracy
      reported separately on seen (82.20%) and unseen (84.85%) text**
- [x] `final_team` may reflect who closed the ticket, not who should have — the
      Repairs→Installs & Demo leak (218 rows) is consistent with scope drift
- [x] Ambiguous requests that cannot be routed from text — **16.80% flagged on
      holdout, 29.27% accuracy when flagged**
- [x] Any bug I found in my own work — **`errors.md` E4: the rename date note
      leaked into canonical names, splitting one queue into two classes**