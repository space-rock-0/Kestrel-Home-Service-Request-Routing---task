# Memo to Ritu Deshpande

**From:** {{author}}  **Re:** Can we switch the routing bot off?

**The decision.** Rule-based suggestion: **{{decision_suggestion}}** ({{decision_reason}}). Keep the matching paragraph, delete the other.

*A. Yes, replace it in two steps.* Run the new router beside the bot for two weeks. Then switch the bot off for every request the router is sure about. The unsure ones, about {{flagged_pct}}% of requests, go to a person who asks one question.

*B. Not yet.* The new router is not clearly better than the bot, so switching now would cost more than the licence saves. Make these rule fixes to the bot this month: {{bot_rule_fixes}}.

**The number.** Measured against where requests actually ended up, on the latest {{n_holdout}} closed requests, the bot sends the right team first time **{{bot_acc_pct}}%** of the time. The new router does it **{{model_acc_pct}}%** of the time. We are 95% sure the true figure is between {{ci_lo_pct}}% and {{ci_hi_pct}}%. Your 90% target measures how closely we copy the bot, which is {{agree_pct}}%. Copying the bot also copies its mistakes: {{bot_mistake_example}}. About {{flagged_pct}}% of requests do not hold enough information to route. The router flags them for a person.

**The rupees.** The licence costs Rs 3,20,000 a year (Rs {{licence_avoided_inr_month_fmt}} a month). The router makes no paid calls: Rs 0 per request and Rs {{hosting_inr_month_fmt}} a month to host, so the cost does not grow with volume. It makes about {{transfers_avoided_per_month}} fewer wrong first touches a month. At Rs {{transfer_cost_inr_fmt}} per transfer that saves Rs {{transfer_saving_inr_month_fmt}} a month. Net: about Rs {{net_benefit_inr_month_fmt}} a month, Rs {{net_benefit_inr_year_fmt}} a year. The transfer saving is an estimate. Farhan, this is the monthly run cost in writing.

**Next week.**
1. {{owner_it}} runs the router in shadow mode beside the bot.
2. {{owner_service}} names two people to review the flagged requests each day and reports disagreements after week one.
3. You set the go or no-go date. We recommend switching the bot off only when the shadow numbers match the table above.
4. {{owner_service}} applies the rule fixes to the bot now. They cut wasted transfers whatever you decide.

**Headcount.** Busiest teams by where requests end up: {{busiest_teams}}. The data has no handling times, so there is no staffing number here.
