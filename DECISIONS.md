# Decisions — the plain-language version

For Tanmay, not for Claude. Every technical file in this repo is written for a
machine to act on. This one is written for you to read once before the
mid-review and again before the viva.

Each entry: what we decided, why, and the one-sentence answer if an examiner
pushes on it. No numbers you do not need.

---

### What this project turned out to be

We set out to build a system that predicts which places will flood. What we
actually produced is a measurement of **how predictable that is at all** — and
the answer is: much less than everyone assumes.

That is not a failure. Almost every project in this space builds a model,
reports a good-looking score, and never checks whether the score means anything.
We checked, repeatedly, and found specific reasons it does not.

The three things we can state that others cannot:

1. **A ceiling.** Even a ranking that cheats — using the test period's own
   answers — beats ours by only 1.6 points out of 24. The limit is in the
   phenomenon, not the method.
2. **A trap.** A standard model score said our model worked. It made no
   difference to the actual decision. We can explain exactly why, and anyone
   building this kind of model can be fooled the same way.
3. **A confound.** Complaint volume in Bengaluru doubled in four years. A naive
   "which places are getting worse" test finds seven rising hotspots — and every
   one disappears once you account for that growth. Two of them are Bellandur
   and Varthur, the most notoriously flood-prone wards in the city, which the
   naive test would have reported as *newly emerging*.

**If challenged — "so your model doesn't work?":** "The model performs at the
measured ceiling for this data. Our contribution is establishing where that
ceiling is and why, which nobody working with civic complaint data had done. A
higher number would have meant we were measuring the wrong thing."

---

### The project is a decision support system, not a prediction system

BBMP already publishes its flood-prone locations. A system that outputs "these
places flood" tells the city what it wrote down years ago.

So we answer three questions it cannot: which of the known spots to send crews
to *tonight*, which places are becoming the next entry on that list, and
whether last year's drain-cleaning actually worked.

**If challenged:** "The city knows where it floods. It doesn't know which twenty
to visit tonight, which places are about to join the list, or whether the money
it spent worked. We answer those three."

---

### We train on Bengaluru, not Delhi

Delhi has a published hotspot list but no downloadable record of *when* things
flooded. Bengaluru has six years of ward-level citizen complaints, its own
flood-prone register, and ward work orders — all free downloads.

Delhi still appears as a demonstration that the method carries to another city,
but with no ground truth, so no scores are reported for it.

**If challenged:** "Bengaluru is where the labels exist. Delhi has the register
but not the incident history, so it demonstrates portability rather than
performance."

---

### We split the complaints into two different things

"Road side drains" is someone asking for a drain to be cleaned — filed on any
dry Tuesday. "Water stagnation" is someone reporting that water is standing
right now.

Lumped together, the first drowns the second, and the model would be asked to
predict a maintenance backlog from rainfall. Separated, the event label responds
to rain three times more strongly.

**If challenged:** "Complaint data mixes event reports with maintenance
requests. Modelling them as one target is a category error, and we measured the
difference before deciding."

---

### We never report accuracy

Flooding is rare. A model that always says "no flood" is right about 98% of the
time and completely useless.

We report precision@20 — of the twenty places we named, how many actually
flooded — because that is the decision a crew supervisor actually makes.

**If challenged:** "Accuracy is meaningless on rare events. We report the metric
that matches the decision: of twenty dispatches, how many were right."

---

### Every score comes with three numbers, never one

A random guess scores about 5%. The city's own "worst twenty" list scores 13.6%.
A perfect oracle scores 37.4%, because on a typical rainy day fewer than twenty
places actually flood, so twenty slots cannot all be right.

A score of 22% sounds like failure alone. Against a 37.4% ceiling it is nearly
60% of what is achievable.

**If challenged:** "We report the achieved score, the baseline it must beat, and
the theoretical ceiling. A number without those two is uninterpretable."

---

### We always train on the past and test on the future

Never a random split. The model learns from earlier years and is tested on later
ones, because that is how it would actually be used.

**If challenged:** "A random split lets the same storm appear in training and
testing. Every result here uses a strict time split."

---

### The ward name matching was done by hand

Complaints record ward names; the register records ward numbers. The spellings
disagree — the same place appears as Halsoor and Ulsoor, Bagalakunte and
Bagalagunte.

Automatic matching produced confident wrong answers, pairing genuinely different
wards. So all 198 were resolved by hand, each with a written reason, and the one
uncertain case is flagged in the file.

**If challenged:** "Fuzzy string matching paired distinct wards. We built the
crosswalk manually with evidence per row, because a wrong ward silently corrupts
every result downstream."

---

### We kept the wards that are *not* on the official register

Ninety-six wards have no entry in the flood-prone register. Dropping them would
have removed 40% of the data while looking like routine cleaning.

They also turn out to be the point: a place that floods but is not on the
official list is exactly what "emerging hotspot" means.

**If challenged:** "Those wards are the population our early-warning output
scans. Excluding them would have deleted the part of the problem we are trying
to solve."

---

### We tried to make the prediction cleverer, measured it, and it did not work

The plan was that knowing how much rain *each specific place* needs before it
floods would beat simply counting past floods. We built that and tested it. It
performed worse.

The reason is mundane: each ward has too few past floods to split across rainfall
levels, so the "clever" number is mostly the simple number with extra noise added.

**If challenged:** "We tested the interaction hypothesis rather than assuming it,
and it failed for a measurable reason — the per-ward history is too thin to
condition on. We report what we measured."

---

### The most important result is a limit, not a win

We asked how much better *any* nightly ranking could possibly be. To find out we
cheated deliberately: we ranked wards using the answers from the test period
itself — the best any method could ever do.

It scored 15.7%. The honest version scores 14.1%. So the entire space available
to any amount of clever feature engineering is about 1.6 percentage points out of
24.

That is the project's central finding. Not "our model is good", but "we measured
how much room there is, and there is almost none — and here is exactly where it
runs out."

**If challenged:** "We established the predictability ceiling rather than
claiming to approach it. A ranking fitted with perfect foresight beats ours by
1.6 points, so the limit is in the phenomenon, not in our method."

---

### Which places flood on a given night genuinely moves — and nothing predicts it

Two facts sit together and that combination is the interesting part.

The set of flooded wards shifts almost completely from one rainy night to the
next — knowing tonight tells you almost nothing about next time. So a fixed list
is not capturing something stable.

And yet nothing we can observe — rainfall, terrain, season, past history —
predicts the shifting.

**If challenged:** "The phenomenon moves, and no available data explains the
movement. Establishing that both are true is more useful than a marginal
improvement would have been."

---

### We do not report AUC, and there is a specific reason

A standard model score (AUC) said our model worked well — 0.75, which looks
convincing. It made no difference whatsoever to the actual decision.

The score was rewarding the model for telling bad nights from quiet nights,
which is easy. The decision needs it to tell places apart *within* one night,
which is what it could not do.

**If challenged:** "Pooled AUC on this kind of data measures the wrong thing. It
credits separating days when the decision compares places within a day. We
demonstrate the gap and report the decision metric instead."

---

*Updated as decisions are made. If something here is not true any more, it is a
bug — tell Claude.*
