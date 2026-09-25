# Innovation Club — dynamic website with a stable-matching team assigner

A Flask + SQLite site for a university Innovation Club, built as a
portfolio piece. Beyond a normal dynamic site (database-backed pages,
a working application form), it includes a real algorithmic feature:
new applicants are matched to project teams using a **stable matching
algorithm**, not a first-come-first-served queue.

## Run it locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 — `innovation_club.db` is created and
seeded automatically on first run (5 sample projects, 4 events, and
5 sample applicants so the Team Matcher page has data immediately).

## Run the algorithm's test suite

```bash
python -m unittest test_matching.py -v
```

9 tests, including a brute-force **stability proof** — it verifies
that no applicant/project pair in the output would both prefer each
other over their current assignment, which is the actual mathematical
definition of a "stable" matching, not just "a" matching.

## What's dynamic

- **Homepage stats** are computed live from the `projects` table.
- **Projects** and **Events** pages read straight from SQLite.
- **Join form** (`/join`) collects an applicant's skills (checkboxes)
  and writes a real row into the `applicants` table, with server-side
  validation and flash messages.
- **Team Matcher** (`/match`) is the core feature — see below.

## The Team Matcher

**Problem:** given a set of applicants (each with skills) and a set
of projects (each with needed skills and a limited number of open
slots), assign applicants to projects so the assignment is *stable*:
no applicant and project would both rather be matched to each other
than to their current assignment. An unstable assignment would just
fall apart in practice — that pair would go work together anyway,
bypassing the official placement.

This is the **Hospitals/Residents problem**, the many-to-one
generalization of the Stable Marriage problem, solved with the
**Gale–Shapley algorithm** (1962) — the same family of algorithm used
for real medical residency placements (and which won a Nobel Prize in
Economics for Shapley and Roth in 2012 for the underlying matching
theory).

**How preferences are derived:** rather than asking applicants and
projects to manually rank each other (impractical at this scale),
both sides' preferences come from **Jaccard similarity** between an
applicant's skill set and a project's required skill set:

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

**The algorithm** (applicant-proposing deferred acceptance):
1. Every unmatched applicant proposes to their best-scoring project
   they haven't already tried.
2. A project with a free slot provisionally accepts.
3. A full project compares the new proposal to its current *worst*
   held applicant — if the new one scores higher, the worst one is
   evicted (and becomes free to propose elsewhere); otherwise the new
   applicant is rejected and moves to their next choice.
4. Repeat until every applicant is matched or has exhausted every
   project they share any skill with.

**Complexity:** O(n · p) proposals in the worst case (n applicants,
p projects), each doing O(log c) work to maintain a sorted "held"
list — trivial at student-club scale, but the same algorithm scales
to national resident-matching programs with tens of thousands of
participants.

Source: `matching.py` (the algorithm) · `test_matching.py` (tests) ·
`/match` route in `app.py` (wires it into the app) ·
`templates/match.html` (the UI).

## Project structure

```
innovation_club/
├── app.py                 # Flask routes
├── models.py               # SQLite schema, seed data, queries
├── matching.py              # stable matching algorithm
├── test_matching.py          # unit tests + stability proof
├── requirements.txt
├── templates/
│   ├── base.html              # shared nav/footer
│   ├── index.html              # homepage: hero, live stats, previews
│   ├── projects.html            # full project list
│   ├── events.html               # upcoming / past events
│   ├── join.html                  # application form (incl. skills)
│   └── match.html                  # Team Matcher results page
└── static/
    ├── css/style.css              # design system
    └── js/script.js                 # hero stat counter animation
```

## Design notes

Visual identity is a "blueprint / lab notebook" theme rather than a
generic SaaS look: paper background, deep ink-navy type, a single
amber accent reserved for calls to action, a faint drafting grid in
the hero, and corner registration marks (instead of rounded shadow
cards) — a nod to technical drawings, since the club is about
prototyping and building.

Typefaces: **Space Grotesk** for display/body text, **JetBrains Mono**
for data-like labels (dates, stage tags, stat numbers, algorithm
scores) — reinforcing the "builder" feel throughout.
