# Memo to Ritu Deshpande

**From:** Sagi Siddhartha  **Re:** Can we switch the routing bot off?

**Our recommendation: replace it, in two steps.** The model clears the bot's own range on every
measure we tried — model interval low 82.4% is 4.9 points above the bot's interval high 77.5% and 16.8% of requests go to a person (limit 30.0%) — and the gap is far too wide to be noise.

The alternative was not "do nothing" — it was to fix the bot's rules. We tested that properly:
applying all seven routing rules from your operations policy to the bot's own decisions lifts it
from 75.00% to **80.02%**. A perfectly tuned rule system still lands **4.5 points short** of the
model. That is the evidence for retiring the bot rather than tuning it, and it is why we did not
recommend the cheaper option.

Run the new router beside the bot for two weeks. Then switch the bot off for every request the router
is sure about. The unsure ones, about 16.8% of requests, go to a person who asks one
question.

*If you would rather not switch yet.* Make these rule fixes to the bot this month:
(1) Billing takes a request only when the payment itself is the problem, so 'I paid for the installation' stops going to Billing; (2) anything reported broken, leaking or showing an error code goes to Repairs, not Consumables; (3) write those two rules into the bot's configuration for the three queues it handles worst -- Billing, Filters & Consumables and Repairs. The other four queues are already 96% correct and should be left alone They cut wasted transfers whichever way you decide.

**The number.** Measured against where requests actually ended up, on the latest 976
closed requests, the bot sends the right team first time **75.0%** of the time. The new
router does it **84.5%** of the time. We are 95% sure the true figure is between
82.4% and 86.7%.

Your 90% target measures how closely we copy the bot, which is 78.6%. We did not chase that
number, and the reason is arithmetic rather than opinion. **The bot itself sends the right team
first time only 75.0% of the time.** So no system that predicts where requests actually
end up can agree with the bot's labels more than roughly 75–77% of the time on new requests. We
tested it rather than asserting it: training the same model directly on the bot's labels scores
**72.75%**. Your ceiling sits below your floor.

Copying the bot also copies its mistakes. Across all 10,822 closed requests, **585** went to
Billing but ended at another team — 524 of those were about paying, not about a fault — and **205**
went to Filters & Consumables but belonged elsewhere, 94 of them purifier faults that belong in
Repairs. On the 976 most recent requests alone those are 51 and 53.

Read the two accuracy figures as different questions. *How often does a request reach the right
team?* — 84.5%, up from 75.0%. *How often do we agree with the old bot?* —
78.6%, and we are not trying to maximise it.

On the 16.8% that go to a person: that is a measure of **our confidence**, not a verdict
on your data. Only about 1% of requests genuinely carry too little information to route. The rest
are ones where the request is ordinary but the router is not certain which team owns it.

**The rupees.** The licence costs Rs 3,20,000 a year (Rs 26,667 a month).
The router makes no paid calls: **Rs 0 per request**, so the cost does not grow with volume. Hosting
is Rs 0 a month *on the assumption it runs on infrastructure you already
pay for* — if it needs its own machine, that is a line we have left for you to fill.

It makes about 69 fewer wrong first touches a month. At Rs
565 per transfer that is Rs 38,985 a month saved.
Net of the licence: about Rs 65,652 a month, Rs
7,87,824 a year.

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

**Headcount.** Busiest teams by where requests end up: Repairs (23.4% of requests), Installs & Demo (14.7%) and Returns & Replacement (14.2%) -- the same three in that order when ranked by hand-offs instead. Hand-offs average 0.36 per
request on top of the first touch, so about 1.36 touches overall. The data has no handling times, so
there is no staffing number here.