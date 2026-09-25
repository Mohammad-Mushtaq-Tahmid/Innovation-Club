"""
Innovation Club — Flask application
------------------------------------
A dynamic website for a university Innovation Club. Projects, events,
and applications are stored in and served from SQLite (models.py).
Applicants are matched to project teams by skill fit using a stable
matching algorithm (matching.py).

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import models
import matching

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-me"  # replace in production


@app.before_request
def ensure_db():
    models.init_db()


@app.route("/")
def home():
    stats = models.get_stats()
    latest_projects = models.get_projects(limit=3)
    upcoming_events = models.get_events(upcoming_only=True, limit=2)
    return render_template(
        "index.html",
        stats=stats,
        projects=latest_projects,
        events=upcoming_events,
    )


@app.route("/projects")
def projects():
    all_projects = models.get_projects()
    return render_template("projects.html", projects=all_projects)


@app.route("/events")
def events():
    upcoming = models.get_events(upcoming_only=True)
    past = models.get_events(upcoming_only=False, past_only=True)
    return render_template("events.html", upcoming=upcoming, past=past)


@app.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", "").strip()
        skills_list = request.form.getlist("skills")
        skills = ",".join(skills_list)
        portfolio = request.form.get("portfolio", "").strip()
        message = request.form.get("message", "").strip()

        errors = []
        if not name:
            errors.append("Please enter your full name.")
        if not student_id:
            errors.append("Please enter your student ID.")
        if not email or "@" not in email:
            errors.append("Please enter a valid email.")
        if not role:
            errors.append("Please select what you'd like to help build.")
        if not skills_list:
            errors.append("Please select at least one skill — it's how we match you to a project.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "join.html", form=request.form, selected_skills=set(skills_list),
                skill_options=models.SKILL_OPTIONS,
            )

        models.add_applicant(name, student_id, email, role, skills, portfolio, message)
        flash("Application received — check the Team Matcher page to see your suggested project.", "success")
        return redirect(url_for("join"))

    return render_template("join.html", form={}, selected_skills=set(), skill_options=models.SKILL_OPTIONS)


@app.route("/match")
def match():
    """
    Runs the stable matching algorithm live over every unmatched
    applicant and every project with open capacity, and shows the
    suggested (not yet confirmed) result.
    """
    applicants = models.get_unmatched_applicants()
    open_projects = models.get_open_projects()

    applicant_dicts = [{"id": a["id"], "skills": a["skills"]} for a in applicants]
    project_dicts = [{"id": p["id"], "skills": p["skills"], "capacity": p["capacity"]} for p in open_projects]

    match_result, unmatched_ids, scores = matching.match_applicants_to_projects(
        applicant_dicts, project_dicts
    )

    projects_by_id = {p["id"]: p for p in open_projects}
    applicants_by_id = {a["id"]: a for a in applicants}

    suggestions = []
    for a_id, p_id in match_result.items():
        suggestions.append({
            "applicant": applicants_by_id[a_id],
            "project": projects_by_id[p_id],
            "score": round(scores[(a_id, p_id)] * 100),
        })
    suggestions.sort(key=lambda s: -s["score"])

    unmatched = [applicants_by_id[a_id] for a_id in unmatched_ids]

    return render_template(
        "match.html",
        suggestions=suggestions,
        unmatched=unmatched,
        has_data=bool(applicants) and bool(open_projects),
    )


@app.route("/match/confirm", methods=["POST"])
def confirm_match():
    """Persists the currently-suggested matching to the database."""
    applicants = models.get_unmatched_applicants()
    open_projects = models.get_open_projects()

    applicant_dicts = [{"id": a["id"], "skills": a["skills"]} for a in applicants]
    project_dicts = [{"id": p["id"], "skills": p["skills"], "capacity": p["capacity"]} for p in open_projects]

    match_result, _, _ = matching.match_applicants_to_projects(applicant_dicts, project_dicts)
    models.confirm_matches(match_result)

    flash(f"Confirmed {len(match_result)} team placement(s).", "success")
    return redirect(url_for("match"))


if __name__ == "__main__":
    models.init_db()
    app.run(debug=True)
