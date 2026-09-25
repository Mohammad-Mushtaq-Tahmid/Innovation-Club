"""
Team-matching algorithm for the Innovation Club.

Problem
-------
We have a set of applicants (each with a set of skills) and a set of
projects (each with a set of needed skills and a fixed number of open
slots, i.e. "capacity"). We want to assign applicants to projects such
that the assignment is STABLE: there is no applicant/project pair that
would both prefer each other over their current assignment. An unstable
assignment would fall apart in practice — that pair would just go work
together anyway, bypassing the official match.

This is the classic "Hospitals/Residents problem" (also called the
College Admissions problem) — a many-to-one generalization of the
Stable Marriage problem solved by the Gale-Shapley algorithm (1962).

Preferences
-----------
Instead of asking applicants and projects to manually rank each other
(impractical at this scale), we derive both sides' preferences from a
Jaccard similarity score between an applicant's skills and a project's
required skills:

    J(A, B) = |A ∩ B| / |A ∪ B|

Each applicant prefers the project with the highest similarity score;
each project prefers the applicant with the highest similarity score.
Ties are broken by lowest id, so results are deterministic.

Algorithm (applicant-proposing deferred acceptance)
-----------------------------------------------------
1. Every unmatched applicant proposes to their most-preferred project
   they haven't already proposed to.
2. A project with a free slot provisionally accepts the proposal.
3. A project that is full compares the new proposal against its
   current worst held applicant. If the new applicant scores higher,
   the worst one is evicted (freed up to propose elsewhere) and the
   new applicant takes the slot. Otherwise the new applicant is
   rejected and moves on to their next-choice project.
4. Repeat until every applicant is either matched or has been
   rejected by every project they have nonzero affinity with.

This always terminates and always produces a matching that is stable
with respect to the derived preferences (proof: standard result for
the Hospitals/Residents algorithm, Gale & Shapley 1962 / Roth 1984).

Complexity
----------
Let n = number of applicants, m = total capacity across all projects.
Each applicant proposes to each project at most once, so there are at
most O(n * p) proposals (p = number of projects). Each proposal does
O(log c) work to maintain a sorted held-list of size ≤ capacity c.
Overall: O(n * p * log c) — for the scale of a student club (tens of
applicants, a handful of projects) this resolves essentially instantly.
"""

from collections import deque


def jaccard(skills_a, skills_b):
    """Similarity between two skill sets, in [0, 1]. 0 if either is empty
    or they share nothing."""
    if not skills_a or not skills_b:
        return 0.0
    intersection = len(skills_a & skills_b)
    union = len(skills_a | skills_b)
    return intersection / union if union else 0.0


def parse_skills(raw):
    """'Python,React, API Design' -> {'Python', 'React', 'API Design'}"""
    if not raw:
        return set()
    return {s.strip() for s in raw.split(",") if s.strip()}


def match_applicants_to_projects(applicants, projects):
    """
    applicants: list of dicts with at least {'id', 'skills' (raw string)}
    projects:   list of dicts with at least {'id', 'skills' (raw string), 'capacity' (int)}

    Returns:
        matches:   dict {applicant_id: project_id}
        unmatched: list of applicant_ids with no viable project
        scores:    dict {(applicant_id, project_id): similarity} for display
    """
    a_skills = {a["id"]: parse_skills(a["skills"]) for a in applicants}
    p_skills = {p["id"]: parse_skills(p["skills"]) for p in projects}
    capacity = {p["id"]: p["capacity"] for p in projects}

    scores = {}
    for a in applicants:
        for p in projects:
            scores[(a["id"], p["id"])] = jaccard(a_skills[a["id"]], p_skills[p["id"]])

    # Rank each applicant's projects by score desc, id asc as tiebreak;
    # drop zero-affinity projects (no point proposing to a project you
    # share nothing with).
    applicant_prefs = {}
    for a in applicants:
        ranked = sorted(
            (p["id"] for p in projects if scores[(a["id"], p["id"])] > 0),
            key=lambda pid: (-scores[(a["id"], pid)], pid),
        )
        applicant_prefs[a["id"]] = ranked

    next_choice_index = {a["id"]: 0 for a in applicants}
    held = {p["id"]: [] for p in projects}  # list of (score, applicant_id), kept sorted ascending
    match = {}

    free = deque(a["id"] for a in applicants if applicant_prefs[a["id"]])

    while free:
        a_id = free.popleft()
        idx = next_choice_index[a_id]
        prefs = applicant_prefs[a_id]

        if idx >= len(prefs):
            continue  # exhausted every project with nonzero affinity — stays unmatched

        p_id = prefs[idx]
        next_choice_index[a_id] += 1
        score = scores[(a_id, p_id)]
        bucket = held[p_id]

        if len(bucket) < capacity[p_id]:
            bucket.append((score, a_id))
            bucket.sort()
            match[a_id] = p_id
        elif bucket and score > bucket[0][0]:
            _, evicted_id = bucket.pop(0)
            bucket.append((score, a_id))
            bucket.sort()
            del match[evicted_id]
            match[a_id] = p_id
            free.append(evicted_id)
        else:
            free.append(a_id)  # rejected outright, will try next choice on next turn

    unmatched = [a["id"] for a in applicants if a["id"] not in match]
    return match, unmatched, scores
