# explain.md — The Kestrel Home problem, in plain words

## 1. The story in 30 seconds

Kestrel Home sells kitchen and home appliances: air fryers, water purifiers, fans, heaters and so on. When a customer has a problem, they send a message (chat, WhatsApp, email) or call.

The company has **7 support teams**. Examples: Technical Support, Installation, Billing, Consumables (filters and parts), and so on.

Someone has to decide **which team should get each message**. Right now a **robot** does this. It is a bought software "routing bot", and it costs **₹3.2 lakh a year**.

The boss, Ritu, says: *"I don't want to pay for this bot any more. Build me something that does the same job, and then we switch the bot off."*

**That's the whole job:** build a replacement for the bot.

---

## 2. A simple picture

Think of a **post office sorting room**. Letters (customer messages) come in. A sorter (the bot) drops each letter into one of 7 boxes (teams).

You are asked to build a new sorter.

---

## 3. What you are given

| File | What it is, simply |
|---|---|
| `train.csv` | Old messages, each with the box the bot put it in |
| `resolution_log.csv` | For those same old messages: **which team really ended up solving it**, and how many times it was passed around |
| `test_unlabelled.csv` | New messages with **no box written**. These are the ones you must sort |
| `teams.csv` | The 7 teams and what each handles |
| `ops-policy.pdf` | The company's rulebook (rules, costs, team changes) |
| `email-thread.txt` | Emails where staff explain their pain |
| `sample_submission.csv` | The answer format: one row per message, with a team name |

---

## 4. What you must hand in (the "deliverables")

1. **`predictions.csv`**: your answer. For every new message, the team it should go to.
2. **A small working app**: you type in a message, it tells you the team and **why**. Must run on any computer without a paid key.
3. **Proof it works**: and also **how often it gets things wrong**.
4. **A one-page memo to Ritu**: written in non-technical language. It says: should we switch the bot off? How accurate is it? How many rupees does it save? What should she do next week?
5. **A screen recording (max 3 minutes)**: what you tried, what you changed, what you threw away.
6. **A filled-in form**: honest answers about your work.
7. **A public GitHub link**: your code.

---

## 5. The big trick in this problem (the part most people miss)

Ritu says: *"The old messages already have the team written on them. Train something that matches those at 90%."*

Sounds easy. **But it's a trap.**

Those team names were written **by the bot**. So the "answer key" is just *what the bot guessed*, and **the bot is often wrong**.

Look at what Meenal (the support manager) says in the emails:

- People who **paid for an installation or repair** get sent to **Billing**. Billing just passes them to another team. Wrong box.
- Water purifier **breakdowns** get sent to **Consumables** (the filters team). Wrong box.
- Many messages just say *"please call me about my purifier"*. Nobody can tell where that goes without asking.

**Analogy:** a student copies answers from a classmate who gets 70% of them wrong, and then proudly says "I match my classmate 90%". They matched the mistakes.

So the **real question** is not "can you copy the bot?" It is **"can you send each message to the team that actually solves it?"**

The file `resolution_log.csv` tells you where each old message **really ended up**. That is the true answer key. Use that to learn from.

---

## 6. How you'll be scored

They keep a secret answer key for the new messages: where those requests **really ended up**. They compare your `predictions.csv` with it.

They also read your memo and form. They care about honesty: **what is wrong with your work and the data** is a part they reward. Also, you must guess your own score in advance, and they compare your guess with the real one.

---

## 7. Other small traps

- **Two teams were renamed** halfway. Old messages use the old names, new ones use new names. Treat them as the same team and use the **current names** in your answer.
- **Old data came from a different system (Zoho)** and has **garbled characters** (like `â€”`). Clean it. Its times are also wrong, so don't use them.
- **Test messages are the most recent ones.** So check your model on recent data, not on a random mix. Otherwise you will fool yourself.
- **Cost matters.** Finance says: *"I won't swap a ₹3.2 lakh licence for an AI bill that grows with every request."* So don't use a paid AI service. A small model on your own computer costs ₹0 per message.
- **Some messages truly can't be sorted** ("call me"). A good system admits "I'm not sure, ask a human" instead of guessing.
- **"Busiest team"** question: Ritu wants it for hiring. You can rank teams, but you don't have staff-time data, so don't invent a headcount.

---

## 8. The business decision you are really helping with

Ritu has to decide: **"Do I renew the bot, or switch to something new?"**

Your job is to give her:

- **The decision:** switch, or not yet.
- **The number:** how often the old bot is right vs how often yours is right, measured honestly.
- **The rupees:** money saved (licence cost avoided + fewer wasted transfers between teams) minus what your thing costs to run.
- **Next week's actions:** simple steps, for example "run it alongside the bot for two weeks first".

---

## 9. A tiny worked example

Customer message: *"I paid for the installation but nobody has come."*

- **Old bot:** sees "paid" and sends it to **Billing**. Billing can't help and passes it on to **Installation**. A wasted step.
- **Your model:** has learned from the history that these end up with **Installation**, so it sends it there directly. One step saved.

Customer message: *"Please call me about my purifier."*

- **Your model:** not sure, so it shows "needs a human to ask one question" and still gives its best guess in the file.

---

## 10. Your plan, in 6 plain steps

1. **Look at the data** and find what is broken (garbled text, renamed teams, how often the bot was wrong).
2. **Decide the right answer key**: where the request really ended up.
3. **Build a simple model** that reads the message text plus the product and warranty and picks a team.
4. **Test it fairly**: train on older data, test on the newest, and compare it to the bot.
5. **Wrap it** in a small app with a "why" explanation, and write the memo, the form and the recording.
6. **Be honest** about where it fails, what it costs and what you couldn't verify.

The detailed version of this plan, with code, is in `BUILD.md`. The form answers are in `submission-form.md`.

---

## 11. Word list

| Word | Meaning |
|---|---|
| Classifier | A program that puts each item into one of several boxes |
| Label | The "correct box" written on an example |
| Train | Show the program many old examples so it learns the pattern |
| Test / holdout | Messages kept hidden to check if it really learned |
| Accuracy | Out of 100 messages, how many went to the right team |
| Transfer | A request passed from one team to another because it landed wrongly |
| Shadow mode | Run the new system quietly beside the old one and compare, before switching |
| Confidence | How sure the model is about its pick |
| Mojibake | Garbled characters from a bad text conversion |

---

## 12. One-line summary

> **Build a cheap, honest replacement for a mistake-prone routing bot, prove it is better using where requests really ended up (not the bot's own guesses), and tell the boss in plain words whether to switch it off and how much money that saves.**
