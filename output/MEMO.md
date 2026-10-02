# Memo to Ritu Deshpande

**From:** {{author}}  **Re:** Can we switch the routing bot off?

**The decision.** Rule-based suggestion: **A** (model interval low 82.4% is 4.9 points above the bot's interval high 77.5% and 16.8% of requests go to a person (limit 30.0%)). Keep the matching paragraph, delete the other.

*A. Yes, replace it in two steps.* Run the new router beside the bot for two weeks. Then switch the bot off for every request the router is sure about. The unsure ones, about 16.8% of requests, go to a person who asks one question.

*B. Not yet.* The new router is not clearly better than the bot, so switching now would cost more than the licence saves. Make these rule fixes to the bot this month: (1) Billing takes a request only when the payment itself is the problem, so "I paid for the installation" stops going to Billing; (2) anything reported broken, leaking or showing an error code goes to Repairs, not Consumables; (3) the three queues the bot handles worst — Billing, Consumables and Repairs — get those two rules written into its configuration. The other four queues are already 96% correct and should be left alone..

**The number.** Measured against where requests actually ended up, on the latest 976 closed requests, the bot sends the right team first time **75.0%** of the time. The new router does it **84.5%** of the time. We are 95% sure the true figure is between 82.4% and 86.7%. Your 90% target measures how closely we copy the bot, which is 78.6%. Copying the bot also copies its mistakes: 585 requests the bot sent to Billing ended at another team — 146 of them were paid installation visits that belong to Installs & Demo — and 315 purifier breakdowns it sent to Consumables ended at Repairs. About 16.8% of requests do not hold enough information to route. The router flags them for a person.

**The rupees.** The licence costs Rs 3,20,000 a year (Rs 26,667 a month). The router makes no paid calls: Rs 0 per request and Rs 0 a month to host, so the cost does not grow with volume. It makes about 69 fewer wrong first touches a month. At Rs 565 per transfer that saves Rs 38,985 a month. Net: about Rs 65,652 a month, Rs 7,87,824 a year. The transfer saving is an estimate. Farhan, this is the monthly run cost in writing.

**Next week.**
1. {{owner_it}} runs the router in shadow mode beside the bot.
2. {{owner_service}} names two people to review the flagged requests each day and reports disagreements after week one.
3. You set the go or no-go date. We recommend switching the bot off only when the shadow numbers match the table above.
4. {{owner_service}} applies the rule fixes to the bot now. They cut wasted transfers whatever you decide.

**Headcount.** Busiest teams by where requests end up: Repairs (23.4% of requests), Installs & Demo (14.7%) and Returns & Replacement (14.2%) — the same three in that order when ranked by hand-offs instead. 1.36 touches per request overall. The data has no handling times, so there is no staffing number here.
