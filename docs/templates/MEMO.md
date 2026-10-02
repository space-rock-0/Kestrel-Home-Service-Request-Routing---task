# Memo to Ritu Deshpande

**From:** {{author}}  **Re:** Can we switch the routing bot off?

**Our recommendation: {{decision_suggestion}}.** {{decision_reason}}

*{{decision_suggestion}}. Yes, replace it in two steps.* Run the new router beside the bot for two
weeks. Then switch the bot off for every request the router is sure about. The unsure ones, about
{{flagged_pct}}% of requests, go to a person who asks one question.

*If you would rather not switch yet.* Make these rule fixes to the bot this month:
{{bot_rule_fixes}}. They cut wasted transfers whichever way you decide.

**The number.** Measured against where requests actually ended up, on the latest {{n_holdout}}
closed requests, the bot sends the right team first time **{{bot_acc_pct}}%** of the time. The new
router does it **{{model_acc_pct}}%** of the time. We are 95% sure the true figure is between
{{ci_lo_pct}}% and {{ci_hi_pct}}%.

Your 90% target measures how closely we copy the bot, which is {{agree_pct}}%. We did not chase that
number, because copying the bot copies its mistakes: {{bot_mistake_example}}. So read the two
figures as different questions. *How often does a request reach the right team?* — that is 84.5%, up
from 75.0%. *How often do we agree with the old bot?* — that is 78.6%, and we are not trying to
maximise it.

On the {{flagged_pct}}% that go to a person: that is a measure of **our confidence**, not a verdict
on your data. Only about 1% of requests genuinely carry too little information to route. The rest
are ones where the request is ordinary but the router is not certain which team owns it.

**The rupees.** The licence costs Rs 3,20,000 a year (Rs {{licence_avoided_inr_month_fmt}} a month).
The router makes no paid calls: **Rs 0 per request**, so the cost does not grow with volume. Hosting
is Rs {{hosting_inr_month_fmt}} a month *on the assumption it runs on infrastructure you already
pay for* — if it needs its own machine, that is a line we have left for you to fill.

It makes about {{transfers_avoided_per_month}} fewer wrong first touches a month. At Rs
{{transfer_cost_inr_fmt}} per transfer that is Rs {{transfer_saving_inr_month_fmt}} a month saved.
Net of the licence: about Rs {{net_benefit_inr_month_fmt}} a month, Rs
{{net_benefit_inr_year_fmt}} a year.

Two honest caveats. The transfer saving is an estimate — recompute it against the interval bounds
before you treat it as a budget line. And we have **not** costed the human review queue: about 122
requests a month, at a few minutes each, is real staff time. Every Rs 100/hour of reviewer cost
takes roughly Rs 1,000 a month off the figure above. We did not guess your rate.

**Next week.**

1. {{owner_it}} runs the router in shadow mode beside the bot — same requests, no change to what
   customers see.
2. {{owner_service}} names two people to review the flagged requests each day and reports
   disagreements after week one.
3. {{owner_service}} applies the bot rule fixes now. They cut wasted transfers whichever way you
   decide.
4. You set the go/no-go date.

**How we would stop.** If the shadow run does not reproduce the numbers in this memo, we do not
switch. {{owner_it}} should treat these as the abort triggers, any one of which means "keep the
bot":

- shadow accuracy below 80% over any full week, or below the bot's own rate on that week;
- the reviewer queue growing past 30% of requests (our ceiling for this design);
- any queue sending more than half its flagged requests to a person for a week running.

Keeping the bot is the default. Switching is the thing you have to argue for.

**Headcount.** Busiest teams by where requests end up: {{busiest_teams}}. Hand-offs average 0.36 per
request on top of the first touch, so about 1.36 touches overall. The data has no handling times, so
there is no staffing number here.