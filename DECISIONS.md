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
### We cannot say whether the spending works — but we can say where it goes

We thought we had shown that wards with more drainage spending improved. We
retracted it.

The apparent effect came entirely from seven wards that received *no* drainage
work at all. Because spending was measured on a log scale, those zeros sat far
out on the axis and dragged the line. Among the 103 wards that actually received
work, spending predicts nothing (p = 0.83). And we had already established that
those seven untreated wards are not a valid comparison group — BBMP left them
alone because it judged they needed nothing.

What survives is a cleaner and more uncomfortable finding. **BBMP allocates
drainage money by ward size, not by flooding history.** Spending is essentially
uncorrelated with how badly a ward actually floods. It correlates with complaint
counts only because bigger wards generate more complaints of everything —
account for area and that disappears too.

"Does the spending work?" needs a control group we do not have. "Does the
spending go where the problem is?" needs no control group at all, and the answer
is no.

**If challenged:** "We retracted the causal claim when the correct diagnostic
plot showed it rested on seven zero-dose wards. The allocation finding is
descriptive, needs no control group, and is the stronger result — a city
spending without reference to its own failure history is exactly the absence of
institutional memory this project is about."

---

### The one sentence the whole project comes down to

Three separate analyses, using different methods on different questions, all
landed in the same place: **the data supports statements about the city, and not
about individual places.**

- How much better could a nightly ranking be? Real room exists, but almost none
  of it belongs to any particular ward.
- Can weather predict how bad tonight is? Yes at the extremes, no in the middle.
- Which places are getting worse? More places are worsening than chance allows
  — and we can name almost none of them.

Three independent supports for one claim. And it has a blunt practical
consequence: systems built on citizen-complaint data should be designed to
answer *"is the city getting worse?"*, not *"which junction do I fix?"* — which
is what nearly every such system is built to answer.

**If challenged:** "We found the same limit three times by three different
routes. That convergence is the result — and it says these systems are being
built to answer a question their data cannot support."

---

### We nearly got a wrong answer by comparing against the wrong baseline

We tested whether individual wards were getting worse by asking "is this ward's
flooding rate rising?" The answer came back: none are, ten are improving.

That was wrong. Flooding complaints were falling city-wide by 22% — comparing
the first four quarters of the window against the last four, events over
complaints in each block. So a ward
that fell only slightly was actually getting *worse relative to the city* — but
the test scored it as improving.

Comparing each ward against the city trend instead of against zero: nine wards
rising, and a permutation test says that's real (p = 0.001).

**If challenged:** "The correct null hypothesis for a per-unit trend is the
population trend, not zero. Testing against zero in a declining population
manufactures false negatives, and we caught it."

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

A random guess scores **4.8%**. The city's own "worst twenty" list scores
**14.1%**. A perfect oracle scores **37.7%**, because on a typical rainy day
fewer than twenty places actually flood, so twenty slots cannot all be right.

A score of 22% sounds like failure alone. Against a 37.7% ceiling it is nearly
60% of what is achievable.

These three come from the same rainfall series — the ECMWF-IFS one the database
holds and the API serves. There is an older set from the coarser ERA5 series
(4.7% / 13.6% / 37.4%) which says the same thing; the two must never be mixed,
because a ceiling from one and a floor from the other puts a number on a scale it
was not measured against. If you are asked for figures, these are the figures.

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
wards. So every one of the 198 was checked by a person and carries a written
reason: **106 matched exactly, 44 after normalising spelling, and 48 needed a
hand decision.** Nothing was left unresolved, and the one genuinely uncertain
case is flagged in the file rather than guessed.

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

### The dashboard forgets your sign-in when you close the tab, on purpose

When you sign in, the browser is handed a token — a string that proves who you
are for the next hour. Where that token is kept is a real choice, and there are
three options.

`localStorage` keeps it until something deletes it. Close the browser, come back
tomorrow, and you are still signed in. That is how most web apps work, and it is
the wrong answer here: this is a municipal system, and the machine an officer
uses is plausibly shared. A token sitting in storage overnight is a signed-in
session waiting for whoever sits down next.

Memory only — which is what we shipped first — keeps it until the page reloads.
Perfectly safe, and slightly too safe: pressing F5, or following a link straight
to one screen, silently signed you out.

We use **`sessionStorage`**, the middle one. The browser itself wipes it when
the tab closes, and it is not shared with other tabs. So a refresh keeps you
signed in and closing the tab signs you out, which is exactly the rule we wanted
and not a compromise on it.

**If challenged — "why not `localStorage`?":** "The rule is that a bearer token
must not survive a tab close on a shared municipal machine. `sessionStorage`
satisfies that by construction — the browser clears it — while surviving a
refresh. `localStorage` would persist until something explicitly removed it,
which is the case the rule exists to prevent."

One detail worth knowing if asked: a stored token is only a claim, so on every
fresh page load the app asks the server who it belongs to before showing
anything. If the token has expired, it is discarded and you get the sign-in
screen. Nothing trusts the browser's copy on its own.

---

### The frontend was living outside version control, and it isn't now

For about a day, the four dashboard screens sat in a folder *next to* the
repository rather than inside it, with no git of their own. They existed on one
disk, in one place, with no backup and nothing on GitHub — a week before the
evaluation. This is recorded because it is worth remembering how ordinary the
mistake looked: everything worked, the tests passed, and nothing about using it
day to day suggested a problem.

It is now `frontend/` inside the repository, tracked and pushed. The backend was
in the same state for a different reason — thirteen commits of finished work
that had never been pushed — and that is fixed too.

**If challenged:** nobody will ask. It is here so the answer to "where is the
code" is one URL rather than two, and so the next person to reorganise this
knows not to split it apart again.

---

### We cannot check whether our "emerging" wards really became hotspots

This is the most honest limitation in the project and it is worth being able to
state it cleanly.

Our second output flags wards that are becoming flood problems but are not yet on
BBMP's official list. The obvious way to check that we are right is to wait: if a
ward we flagged in 2023 appears on the city's list in 2025, we called it.

We cannot do that, because **BBMP's published list carries no dates.** We checked
all three of the map files they publish. Two of them contain nothing but an
internal id number per location. The third adds a name, a ward number and a zone.
None of them says when a location was added. So there is no way to ask "what did
the city add last year", and therefore no way to score our flags against it.

We kept the empty column in the database rather than deleting it, and the system
says so out loud — the emerging screen carries a banner reading
`ground_truth_available: false` with the reason. Deleting the column would have
looked tidier and quietly removed the evidence that the check is missing.

**If challenged — "so how do you know the emerging detector works?":** "Against
the city's own additions, we cannot, and we say so on the screen. What we can
show is that flagged wards stay above the city norm afterwards — ten of ten did,
p = 0.0001. That is internal validation, and we label it as such rather than
implying external confirmation we do not have."

---

### The "is it on the official list?" flag lives in one specific place, deliberately

A small thing that would be easy to get wrong later, recorded so it is not.

Whether a ward is on BBMP's flood register is stored in
`data/reference/ward_crosswalk.csv`, not in the database's `locations` table. The
database does have a `is_known_hotspot` flag, but it is set on the 398 individual
register *locations*, and it is deliberately false for all 198 *wards*.

That looks like an oversight and is not. Only 200 of the 398 register locations
carry a ward number at all, so a ward-level flag computed from the database would
be built from half the register. The crosswalk was assembled by hand and checked,
and where the two disagree — exactly one ward, number 65 — the hand check is the
one that is right: the register calls it Kadu Malleshwar, the 2015 ward map calls
it Subedarapalya, and we left it unpaired rather than guess.

**Why it matters:** our emerging result is restricted in advance to the 42
eligible wards that are *not* on the register. Code that read the flag from the
database would find every ward marked "not on the register" and widen that pool
to all 103 — which would turn a pre-declared restriction into fishing for a
result. Same number, wrong place, invalid finding.

---

*Updated as decisions are made. If something here is not true any more, it is a
bug — tell Claude.*
