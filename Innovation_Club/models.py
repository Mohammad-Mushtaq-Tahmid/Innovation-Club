"""
Data layer for the Innovation Club site.
Uses plain sqlite3 (no ORM) to keep the dependency list to just Flask.
"""

import sqlite3
from datetime import date

DB_PATH = "innovation_club.db"

# Skill tags used consistently across project requirements and
# applicant skills, so the matching algorithm compares like with like.
SKILL_OPTIONS = [
    "Python", "JavaScript", "React", "Mobile", "API Design",
    "Hardware", "Data / AI", "Figma / UX", "Marketing", "Video",
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            stage TEXT NOT NULL,
            team_size INTEGER NOT NULL,
            tag TEXT NOT NULL,
            skills TEXT NOT NULL DEFAULT '',
            capacity INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            event_date TEXT NOT NULL,
            location TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            skills TEXT NOT NULL DEFAULT '',
            portfolio TEXT,
            message TEXT,
            matched_project_id INTEGER,
            submitted_at TEXT NOT NULL
        )
    """)

    conn.commit()

    # Seed sample data only if tables are empty, so re-running app.py
    # doesn't duplicate rows.
    if cur.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0:
        cur.executemany(
            """INSERT INTO projects
               (title, summary, stage, team_size, tag, skills, capacity)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                ("CampusRoute", "Real-time shuttle tracking for the university bus loop.",
                 "Launched", 4, "Mobile", "Mobile,API Design", 1),
                ("StudyPair", "Matches students into study groups by course and schedule overlap.",
                 "MVP", 3, "Web", "Python,React,API Design", 2),
                ("GreenBin", "Sensor-based bin that sorts recycling from waste automatically.",
                 "Prototype", 2, "Hardware", "Hardware,Python,Data / AI", 3),
                ("LectureNotes AI", "Turns lecture audio into structured, searchable notes.",
                 "MVP", 2, "AI/ML", "Python,Data / AI,React", 2),
                ("MarketDay", "A pop-up marketplace app for student-run small businesses.",
                 "Prototype", 2, "Web", "React,Figma / UX,Marketing", 3),
            ],
        )

    if cur.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO events (title, description, event_date, location) VALUES (?, ?, ?, ?)",
            [
                ("Build Night: Week 1", "Open studio hours — bring an idea or join a team already forming.", "2026-10-02", "Innovation Lab, Rm 204"),
                ("Pitch Practice", "Run your pitch in front of the group before demo day.", "2026-10-16", "Innovation Lab, Rm 204"),
                ("Demo Day", "Teams show what they've shipped this term to guests and alumni.", "2026-11-20", "Main Auditorium"),
                ("Founder Talk: From Prototype to First User", "Alumni founder on getting your first ten users.", "2026-09-10", "Innovation Lab, Rm 204"),
            ],
        )

    # A few sample applicants so the Team Matcher page has something to
    # show immediately, without requiring real form submissions first.
    if cur.execute("SELECT COUNT(*) FROM applicants").fetchone()[0] == 0:
        cur.executemany(
            """INSERT INTO applicants
               (name, student_id, email, role, skills, portfolio, message, matched_project_id, submitted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL, datetime('now'))""",
            [
                ("Mei Lin", "20260031", "mei.lin@example.edu", "Engineering", "Python,React,API Design", "", ""),
                ("Arjun Patel", "20260044", "arjun.p@example.edu", "Hardware", "Hardware,Data / AI", "", ""),
                ("Sofia Reyes", "20260058", "sofia.r@example.edu", "Product / Design", "Figma / UX,Marketing", "", ""),
                ("Wei Chen", "20260071", "wei.chen@example.edu", "Engineering", "Python,Data / AI", "", ""),
                ("Nadia Hassan", "20260083", "nadia.h@example.edu", "Business / Ops", "Marketing,Figma / UX", "", ""),
            ],
        )

    conn.commit()
    conn.close()


def get_stats():
    conn = get_db()
    builders = conn.execute("SELECT COALESCE(SUM(team_size), 0) FROM projects").fetchone()[0]
    active_projects = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE stage != 'Launched'"
    ).fetchone()[0]
    shipped = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE stage = 'Launched'"
    ).fetchone()[0]
    conn.close()
    return {"builders": builders, "active_projects": active_projects, "shipped": shipped}


def get_projects(limit=None):
    conn = get_db()
    q = "SELECT * FROM projects ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    rows = conn.execute(q).fetchall()
    conn.close()
    return rows


def get_open_projects():
    """Projects that still have capacity for new members."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects WHERE capacity > 0 ORDER BY id").fetchall()
    conn.close()
    return rows


def get_events(upcoming_only=False, past_only=False, limit=None):
    conn = get_db()
    today = date.today().isoformat()
    if upcoming_only:
        q = "SELECT * FROM events WHERE event_date >= ? ORDER BY event_date ASC"
        params = (today,)
    elif past_only:
        q = "SELECT * FROM events WHERE event_date < ? ORDER BY event_date DESC"
        params = (today,)
    else:
        q = "SELECT * FROM events ORDER BY event_date ASC"
        params = ()
    if limit:
        q += f" LIMIT {int(limit)}"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def add_applicant(name, student_id, email, role, skills, portfolio, message):
    conn = get_db()
    conn.execute(
        """INSERT INTO applicants
           (name, student_id, email, role, skills, portfolio, message, matched_project_id, submitted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, NULL, datetime('now'))""",
        (name, student_id, email, role, skills, portfolio, message),
    )
    conn.commit()
    conn.close()


def get_unmatched_applicants():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM applicants WHERE matched_project_id IS NULL ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def get_matched_applicants():
    conn = get_db()
    rows = conn.execute("""
        SELECT applicants.*, projects.title AS project_title
        FROM applicants
        JOIN projects ON projects.id = applicants.matched_project_id
        ORDER BY applicants.id
    """).fetchall()
    conn.close()
    return rows


def confirm_matches(matches):
    """
    matches: dict of {applicant_id: project_id}.
    Assigns each applicant to their matched project, and moves one unit
    of capacity from the project's open slots into its team size.
    """
    conn = get_db()
    cur = conn.cursor()
    for applicant_id, project_id in matches.items():
        cur.execute(
            "UPDATE applicants SET matched_project_id = ? WHERE id = ?",
            (project_id, applicant_id),
        )
        cur.execute(
            "UPDATE projects SET capacity = capacity - 1, team_size = team_size + 1 "
            "WHERE id = ? AND capacity > 0",
            (project_id,),
        )
    conn.commit()
    conn.close()
