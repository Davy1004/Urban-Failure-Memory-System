# Decisions — the plain-language version

For Tanmay, not for Claude. Every technical file in this repo is written for a
machine to act on. This one is written for you to read once before the
mid-review and again before the viva.

Each entry: what we decided, why, and the one-sentence answer if an examiner
pushes on it. No numbers you do not need.

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

### The memory features are about rainfall response, not counts

We measured this rather than assumed it: simply counting past floods per ward
reproduces the city's existing list and stops there. Knowing *more* history adds
nothing.

What matters is how much rain each specific place needs before it floods. Two
roads get the same 60 mm; one goes under and one does not. That difference is
the system.

**If challenged:** "We measured that frequency-based memory saturates. The
predictive signal is in how each location responds to rainfall, not how often it
has failed."

---

### Rainfall is currently city-wide, and we say so

The free weather data has grid cells about the size of Bengaluru itself, so
almost every ward reads the same rainfall value. We are testing finer sources.

Until then, results are reported as city-level, not as if we had per-ward rain.

**If challenged:** "Reanalysis at 25 km cannot resolve variation inside a 30 km
city. We state that limitation rather than implying spatial precision we do not
have."

---

*Updated as decisions are made. If something here is not true any more, it is a
bug — tell Claude.*
