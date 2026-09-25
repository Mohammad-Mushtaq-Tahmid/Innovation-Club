"""
Tests for matching.py — run with:  python -m pytest test_matching.py -v
(or python -m unittest test_matching.py if pytest isn't installed)
"""

import unittest
from matching import jaccard, parse_skills, match_applicants_to_projects


class TestJaccard(unittest.TestCase):
    def test_identical_sets(self):
        self.assertEqual(jaccard({"Python", "React"}, {"Python", "React"}), 1.0)

    def test_disjoint_sets(self):
        self.assertEqual(jaccard({"Python"}, {"Figma"}), 0.0)

    def test_partial_overlap(self):
        # {Python} intersect {Python, React} = 1, union = 2 -> 0.5
        self.assertAlmostEqual(jaccard({"Python"}, {"Python", "React"}), 0.5)

    def test_empty_set_is_zero(self):
        self.assertEqual(jaccard(set(), {"Python"}), 0.0)
        self.assertEqual(jaccard(set(), set()), 0.0)


class TestParseSkills(unittest.TestCase):
    def test_basic_split(self):
        self.assertEqual(parse_skills("Python,React,API Design"),
                          {"Python", "React", "API Design"})

    def test_handles_whitespace(self):
        self.assertEqual(parse_skills(" Python , React "), {"Python", "React"})

    def test_empty_string(self):
        self.assertEqual(parse_skills(""), set())


class TestMatching(unittest.TestCase):
    def test_perfect_matches_when_capacity_allows(self):
        applicants = [
            {"id": 1, "skills": "Python,React"},
            {"id": 2, "skills": "Hardware"},
        ]
        projects = [
            {"id": 10, "skills": "Python,React,API Design", "capacity": 1},
            {"id": 20, "skills": "Hardware,Data / AI", "capacity": 1},
        ]
        match, unmatched, _ = match_applicants_to_projects(applicants, projects)
        self.assertEqual(match[1], 10)
        self.assertEqual(match[2], 20)
        self.assertEqual(unmatched, [])

    def test_no_overlap_leaves_applicant_unmatched(self):
        applicants = [{"id": 1, "skills": "Marketing"}]
        projects = [{"id": 10, "skills": "Hardware", "capacity": 1}]
        match, unmatched, _ = match_applicants_to_projects(applicants, projects)
        self.assertEqual(match, {})
        self.assertEqual(unmatched, [1])

    def test_capacity_is_respected(self):
        # 3 applicants all wanting the same single-slot project
        applicants = [
            {"id": 1, "skills": "Python"},
            {"id": 2, "skills": "Python"},
            {"id": 3, "skills": "Python"},
        ]
        projects = [{"id": 10, "skills": "Python", "capacity": 1}]
        match, unmatched, _ = match_applicants_to_projects(applicants, projects)
        self.assertEqual(len(match), 1)
        self.assertEqual(len(unmatched), 2)

    def test_better_fit_displaces_weaker_one_when_full(self):
        # Both want the same project; project prefers whoever scores higher.
        # Applicant 2 (perfect match) should win the single slot even
        # though applicant 1 proposes first.
        applicants = [
            {"id": 1, "skills": "Python"},                # partial match
            {"id": 2, "skills": "Python,React,API Design"},  # perfect match
        ]
        projects = [{"id": 10, "skills": "Python,React,API Design", "capacity": 1}]
        match, unmatched, scores = match_applicants_to_projects(applicants, projects)
        self.assertEqual(match.get(2), 10)
        self.assertEqual(unmatched, [1])

    def test_matching_is_stable(self):
        """
        A matching is stable if there is no (applicant, project) pair
        that both prefer each other over their current assignment.
        This brute-forces that check over a small randomized-ish case.
        """
        applicants = [
            {"id": 1, "skills": "Python,React"},
            {"id": 2, "skills": "Hardware,Data / AI"},
            {"id": 3, "skills": "Figma / UX,Marketing"},
        ]
        projects = [
            {"id": 10, "skills": "Python,React,API Design", "capacity": 1},
            {"id": 20, "skills": "Hardware,Data / AI", "capacity": 1},
            {"id": 30, "skills": "Figma / UX,Marketing", "capacity": 1},
        ]
        match, unmatched, scores = match_applicants_to_projects(applicants, projects)

        project_capacity = {p["id"]: p["capacity"] for p in projects}
        project_current_occupants = {p["id"]: [] for p in projects}
        for a_id, p_id in match.items():
            project_current_occupants[p_id].append(a_id)

        for a in applicants:
            a_id = a["id"]
            a_current_project = match.get(a_id)
            a_current_score = scores.get((a_id, a_current_project), 0) if a_current_project else 0

            for p in projects:
                p_id = p["id"]
                if p_id == a_current_project:
                    continue
                pair_score = scores[(a_id, p_id)]
                if pair_score <= a_current_score:
                    continue  # applicant doesn't even prefer this project, no instability risk

                occupants = project_current_occupants[p_id]
                if len(occupants) < project_capacity[p_id]:
                    self.fail(
                        f"Instability: applicant {a_id} prefers open project {p_id} "
                        f"over current match {a_current_project}"
                    )
                else:
                    worst_occupant_score = min(scores[(o, p_id)] for o in occupants)
                    if pair_score > worst_occupant_score:
                        self.fail(
                            f"Instability: applicant {a_id} and project {p_id} "
                            f"would both prefer each other over current matches"
                        )


if __name__ == "__main__":
    unittest.main()
