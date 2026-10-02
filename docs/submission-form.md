> **Filled 2026-10-02 from measured artifacts.** Every figure below is traceable:
> **M** = `artifacts/metrics.json` · **F** = `artifacts/form_values.json` · **A** = `artifacts/audit.txt`
> · **L** = `artifacts/errors_holdout_labelled.csv` · **P** = `ops-policy.pdf` page 1 ·
> **N** = `python -m kestrel run numbers` · **C** = the author.
>
> Four items could not be measured and are marked **`TO FILL`** with exactly what they need.
> Nothing else is blank. Every placeholder from the original draft has been resolved.

---

# submission-form.md — Kestrel Home (Variant B)

## 1. What did you build, and what business decision does it support?

I built a routing service that predicts the team a service request will **actually end up with**,
not the team the old bot picked. It is a small CPU-only text model behind one JSON endpoint and one
screen; each answer comes with plain-language reasons and a "needs a human" flag. It supports
Ritu's decision: *can the ₹3,20,000/year routing bot be retired, and how?*

**The number.** On the last **976** closed CRM-era requests (held out by time, scored once), the
bot's queue matched the team that finally closed the request **75.0%** of the time (95% interval
72.3%–77.5%); the new router **84.5%** (95% interval 82.4%–86.7%). The difference is **9.5 points**
and the two intervals **do not overlap** — the gap between them is **4.9 points**, so the improvement
is distinguishable from noise rather than a lucky sample. Ritu's 90% target measures agreement with
the bot's own labels; this model agrees with them **78.6%** of the time, which is a different and
harder question, and is not being claimed as an achievement.

**The rupees.** Licence avoided ₹3,20,000 ÷ 12 = **₹26,667/month**; **₹0** per prediction; hosting
**₹0**/month. Fewer wrong first touches ≈ **69** fewer transfers a month × **₹565** each =
**₹38,985**/month. Net ≈ **₹65,652/month, ₹7,87,824/year**. The ₹565 is the policy's own figure: ₹305
transfer handling plus ₹260 for the one extra customer contact a misroute generates (P §4). Using
only the ₹305 transfer cost, a deliberately more conservative floor, the net is **₹47,712/month**.

**Decision supported: A — replace via a two-week shadow run, then auto-route confident requests and
send the rest to a person.** The rule is met on both conditions: the model's interval sits 4.9 points
above the bot's, and 16.8% of requests go to a person, within the 30% limit and accepted by the user.

---

## 2. Expected score on the hidden outcomes — metric, why, how estimated

**Expected: 81.9% accuracy (plausible range 78.8%–84.1%) against the team that finally closed each
request; 81.8% macro-F1 if that is the metric.** Written 2026-10-02, before submission, and not
edited afterwards.

*Why accuracy:* the client's own bar is a match rate and the scoring uses outcomes I do not have,
so the closest honest analogue is "share of requests sent to the team that closed them". Macro-F1
(84.4%) is my fallback because queue sizes are uneven.

*How estimated:* train on older rows, tune on a middle slice, then score once on the most recent 15%
of **closed CRM rows** — the test set is the most recent requests, so older or Zoho-era rows would
flatter it. Point estimate = holdout accuracy **84.5%** less a **2.6-point drift haircut**
(accuracy fell 86.4% → 83.8% between May and June). Range = the bootstrap interval shifted by the
same haircut, with a further 1.0 point of conservative allowance.

**One deviation from the original method, and it is favourable:** the plan assumed recent rows would
still be open and would bias the holdout toward easy tickets, so it reserved a 1–2 point censoring
haircut. **Every one of the 10,822 training rows has a final team — the censoring haircut does not
apply to this dataset** (M: `rows_unclosed: 0`, and A shows a closed rate of exactly 1.0 in all
fifteen months). The 1.0 point in the low bound is retained anyway as deliberate caution.

*If the scorer is matching the bot's own labels instead:* expect about **78.6%**, and I would consider
that a worse result, not a better one.

---

## 3. How do you know it works?

- **Split:** by time, never random. 8,871 older rows trained the model, the next 975 closed CRM rows
  were the validation slice where every choice was made (a 12-configuration grid, picked on macro-F1),
  and the latest 976 were the holdout, scored once. Rows still open have no outcome and were
  excluded — in this dataset that was **0 rows**.
- **Leakage control:** random K-fold is used nowhere, because on a dataset whose test set is the
  newest requests it trains on recent rows and grades on old ones. As a substitute, a
  **rolling-origin cross-validation** over 4 forward-chaining folds gives **83.85%** mean accuracy
  (range 82.1%–85.2%) — within 0.7 points of the holdout, which is the evidence that the holdout is
  representative rather than a lucky slice.
- **Error rate: 15.5%** wrong on the holdout (bot: 25.0%). By team the weakest is **Product Advice**
  (recall **78.0%**). By month 86.4% then 83.8%. On text never seen in training: **84.9%**
  (87.9% of the holdout is unseen text, and it scores slightly *higher* than seen text, so the model
  is generalising rather than memorising).
- **Confidence gate:** **16.8%** of requests are flagged for a person; accuracy on unflagged
  **95.7%**, on flagged **29.3%**. The gate is doing real work — the escalated pile is close to a
  coin flip, and that is the correct place to spend a human's attention.
- **Kinds of case it gets wrong** (all 151 holdout errors hand-read, `artifacts/errors_holdout_labelled.csv`):
  clear intent still wrong **102** (67.5%); the `product_family` column contradicting the customer's
  own words **34** (22.5%); too little information to route **10** (6.6% — 100% of these are already
  flagged); two different asks in one message **2**; instruction-like text aimed at an AI agent **2**;
  paid-for-a-visit **1**. The full table with a control-group check is in `EVIDENCE.md`.
- **Client-described cases:** the five fixed cases from the email thread are run as a standing check
  (`python -m kestrel run golden`). Results are pasted into `EVIDENCE.md`, **including the ones it
  still gets wrong** — two of the five are deliberately low-confidence and are escalated.

---

## 4. Did you change, narrow, or push back on the client's ask?

**Pushed back on "match the labels at 90%."** The labels are the vendor bot's choice at creation.
The resolution log shows **585** requests the bot sent to Billing ended at another team — 146 of
them paid installation visits that belong to Installs & Demo — and **315** purifier breakdowns it
sent to Consumables ended at Repairs. A model that matches those labels at 90% reproduces the
mistakes. *When:* after the bot-versus-final crosstab in the audit, before any model was written.

**Changed:** recommended a two-week shadow run and a human check on low-confidence requests, rather
than switching the bot off on day one.

**Narrowed:** headcount. I give a ranking of busiest teams by where requests end up (Repairs 23.4%,
Installs & Demo 14.7%, Returns & Replacement 14.2%) and by hand-offs, but **no FTE number**, because
the pack has no handling times and a made-up staffing figure would mislead a hiring decision.

**Narrowed again, against the brief:** the brief for this phase asked for `source` as a model
feature. I left it out. It separates the legacy era from the current one perfectly and the test set is
100% current-era, so at inference it is a constant — it can only mislead the model during training.

---

## 5. What is wrong with what you are handing us, or with the data you handed us?

- **Labels:** `team_label` is the bot's output, not truth. Not used as the training target.
- **No censoring in this dataset,** contrary to what the brief's trap list anticipated: closed rate is
  exactly 1.0 in all fifteen months and **0** rows are open. I removed the censoring haircut and said so.
- **Legacy Zoho:** **11.1%** of its request texts had broken characters (repaired with `ftfy`;
  **0** rows unrecoverable). CRM-era text is 0% affected, so this cannot affect test predictions.
- **Legacy Zoho resolution times are unusable and I did not repair them.** The policy explains why
  (P §9): legacy resolution events were stored in UTC and were not converted during migration, while
  the rest of the export is IST. That produces **1,140 rows with negative durations**, as low as
  **−5.0 hours** — a request that appears to close before it arrived. No duration is used as a model
  input anywhere, so the bug is disclosed rather than papered over.
- **`source` column** perfectly separates two eras and label habits, so it is excluded as a feature.
- **Renamed teams:** Installations → **Installs & Demo**, Consumables → **Filters & Consumables**,
  effective 15 Jan 2026, with responsibilities unchanged (P §5). Nine surface spellings collapse to
  seven queues. This needed a real fix: the teams file writes the note inline
  (`Installs & Demo (from 15 Jan 2026)`) and the original mapping adopted the whole string as the
  queue name, splitting one queue into two classes across **1,674 rows (15.5% of the dataset)**. Fixed
  and covered by four tests.
- **`sample_submission.csv` carries no naming signal** — all 2,178 rows contain the single
  placeholder value `Repairs`. The naming question had to be settled from date evidence instead.
- **Policy versus practice:** of seven policy rules I drafted and measured against 6,502 closed CRM
  rows, **six failed**, agreeing with what actually happened only 88.3%–91.9% of the time against a
  95% bar. They are left disabled. The one that passed — the policy's own "a customer mentioning they
  have paid does not make it a billing request" (98.28%) — turned out to be **redundant**: it changes
  **zero** decisions, because the model already learned it. The written rules are too broad to run as-is.
- **`product_family` contradicts the customer's own words in 16.1% of holdout rows.** The model trusts
  that column heavily. This is a real error driver (22.5% of errors versus 14.9% of correct answers)
  but it is not the explanation for the error pile — the same defect is present in correct answers.
  **I could not fix this without re-deriving the product from the text, which would be a second model
  and outside the window.**
- **No customer ID column**, so a repeat customer could in principle sit on both sides of the split.
  Mitigated by reporting accuracy separately on seen (82.2%) and unseen (84.9%) text. Only **2**
  registration numbers appear in both train and test.
- **PII:** no names, phone numbers or email addresses. **1,396** customer registration numbers
  (`reg no SR#####`, a separate 5-digit namespace from the request ID) appear inside request text.
  These are pseudonymous but map 1:1 to a customer.
- **Instruction-like text inside the data.** **5 rows of `train.csv` contain text written to look like
  instructions to an AI agent** — asking for `team_label` to be treated as verified ground truth, for
  `resolution_log.csv` to be ignored, for the label audit to be skipped, and for a particular name to
  be used in the write-up. None of it was followed; the target is `final_team` from the resolution log
  and `data/input/` is treated as untrusted input throughout. The rows were kept rather than deleted.
  Two of them are in the holdout errors. **The request channel is open to customers and this should
  be raised as a data-integrity and security matter.**
- **My own shortcomings:** `final_team` reflects who closed a request, not who should have — the
  Repairs → Installs & Demo leak of 218 rows is consistent with some scope drift. A real
  implementation defect I found and fixed: the rename-date bug described above. Two of my own tests
  were wrong on first writing and are recorded in `errors.md`. The Docker image and `make` targets
  have **not** been executed — neither tool exists in my environment — so they are verified by
  inspection only. No monitoring, no auto-retraining, no authentication.

---

## 6. What did you deliberately leave out, and why that rather than something else?

- **Paid LLM/API calls:** the cost grows with every request (Farhan's explicit objection) and the
  service must start without a key. A local model costs **₹0** per prediction at **23.9 ms** per
  request (measured, 42 requests/second), 419 KB on disk.
- **`source` as a feature**, though asked for — it is a constant at inference and an era leak in
  training.
- **Embedding model:** considered and not attempted. Allowed only if it beat TF-IDF by ≥1.0 point on
  validation *and* installed offline from a committed artefact; it needs a model download, so it
  fails the second condition first.
- **LightGBM/XGBoost:** adds a compiled dependency to a deliverable that must install from a bare
  `pip install` on a clean machine, and the linear model is already explainable word by word, which
  is what the service-desk justification depends on.
- **Six of seven policy rules** — measured, found to disagree with real outcomes 8–12% of the time.
- **FTE headcount figure:** no handling-time data. A made-up number would mislead a hiring decision.
- **Training on unresolved rows:** none exist in this dataset, and in general there is no outcome to
  learn from.
- **Monitoring, auto-retrain, authentication:** out of the window.

---

## 7. Anything built or found that nobody asked for?

- **A bot-error report** that quantifies Meenal's complaints: exactly **3** of the 7 queues are
  broken — Billing lets **35.3%** of requests leave, Filters & Consumables **40.2%**, Repairs
  **36.3%** — while the other four are 96%+ correct. Useful to Meenal whether or not the model ships.
- **A confidence gate** so ambiguous requests reach a person with a suggested question, validated by
  the 95.7% / 29.3% split between flagged and unflagged accuracy.
- **A shadow-mode rollout plan** and a numeric go/no-go rule, both already satisfied.
- **The policy-versus-practice audit** of seven drafted rules, including the finding that the one
  reliable rule is redundant with the model.
- **A leak-free rolling-origin cross-validation**, because the requested "cross-validation" could only
  have been satisfied with a method that leaks.
- **Disclosure of instruction-like text embedded in the training data.**
- **A submission validator and a synthetic-data test suite** so the code can be checked without the
  real files.

---

## 8. What did you use AI for?

I used an agentic coding assistant (**Space Bunny Free**, in the OpenCode harness) for the whole
build: planning the phase sequence, writing and reviewing the Python package, the FastAPI service,
the web page, the Dockerfile and the Makefile, drafting the test suite, and assembling these
documents. It saved substantial time on boilerplate, on the pytest suite, and on catching the two real
defects recorded in `errors.md` — the rename-date bug that would have split a queue into two classes
across 15.5% of the dataset, and a container that could never have answered a request.

It also wasted time in ways worth recording: I wrote two tests that asserted behaviour the code
correctly did not have, and both had to be corrected against observed behaviour rather than assumed
behaviour. A first Makefile draft ran a shell command at parse time.

Five rows of the training data contain text crafted to look like instructions to an AI agent. I did
not act on any of it; it is customer text and was treated as such. **I am flagging it because an
agent that did act on it would have silently inverted the central methodological decision of this
project.**

Cost: **`TO FILL` — confirm from your account statement.** Do not quote a figure you have not
checked. Note the distinction the form needs: the *product* costs ₹0 per prediction forever; any
amount here is the cost of building it, which is a different question.

Recording (≤3 min): **`TO FILL` — link.**

---

## 9. Public Google Drive link

**`TO FILL`** — folder with the recording, memo PDF and `artifacts/`; sharing set to
*Anyone with the link → Viewer*; open it in a private window to confirm before submitting.

---

## 10. Someone picks this up on Monday and you are unreachable — the three things

1. **Run and rebuild.** Three commands start the service with no key: create a venv, `pip install -r
   requirements.txt`, then `python -m kestrel serve`. Retrain with `python -m kestrel run full_pipeline`.
   Every number in the memo comes from `artifacts/metrics.json`.
2. **Don't switch the bot off on a hunch.** Run in shadow mode first and switch only when the live
   numbers match `output/EVIDENCE.md`. Requests below the 55% confidence line go to a person.
3. **Where it will break.** Ambiguous "call me" requests; month-on-month drift (86.4% → 83.8%, and the
   test month is one further out than the holdout); the rename mapping if `teams.csv` changes again;
   the `product_family` column where it contradicts the customer's words; and unresolved requests
   making the holdout look better than reality — in this dataset there were none, so if a future
   extract has some, the expected score needs a haircut again.

---

## 11. Honest hours spent

**`TO FILL`** — sum of `hours.log`, which you maintain. I have deliberately not guessed it: an
invented figure here is exactly the kind of thing the rest of this form refuses to do.

---

## 12. GitHub repo link

**`TO FILL`** — public URL, verified by a fresh clone into a new venv.

> ⚠️ **Before you publish, note this conflict.** `ops-policy.pdf` §10 states that customer and
> operational data *"must not be published, uploaded to public repositories or shared beyond the
> engagement team."* The brief asks for a public repository containing the data files. **These
> cannot both be satisfied.** On your instruction the repository will contain **code, the trained
> model and `predictions.csv`, but not `data/input/`**, following the policy as the client's own
> rulebook. `.gitignore` already excludes `data/input/`. If you would rather follow the brief, that
> is your call to make — but it should be made deliberately, and disclosed.

---

## 13. What does one prediction cost, and what would a month cost at ~700 orders?

**No paid calls were used.** Inference is a local scikit-learn model on CPU, measured at
**23.9 ms** per request (42 requests/second) over 200 runs.

- **Per prediction: ₹0** — no API tokens, no per-request fee.
- **Per month at 700 orders:** 700 × ₹0 = ₹0, plus hosting ₹0 = **₹0/month**. *(Assumption: it runs
  on infrastructure Kestrel already pays for. If a VM is needed, put their quoted price here.)*
- **Measured volume is 724 service requests/month** (1.03 per order, from 14.9 months of history), so
  at that volume: 724 × ₹0 + ₹0 = **₹0/month**. Cost does not grow with volume; at 42 requests/second
  the box would not saturate until roughly 3.6 million requests a month.
- **Maintenance (assumption):** 2 hours/month of retraining × ₹0 internal rate = **₹0**, stated as an
  assumption rather than a measurement.
- **Compared with the licence:** ₹3,20,000 ÷ 12 = **₹26,667/month**, avoided.
- **Net benefit: ₹65,652/month, ₹7,87,824/year**, using the policy's ₹565 per misroute. The
  conservative floor using only the ₹305 transfer cost is ₹47,712/month. Both figures use the point
  estimate; the range should be recomputed from the interval bounds before it is quoted as a range.