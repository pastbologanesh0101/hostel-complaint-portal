from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth_helpers import login_required_student
from ..db import CATEGORIES, PRIORITIES, get_db, now_iso

bp = Blueprint("student", __name__, url_prefix="/student")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        room_number = request.form["room_number"].strip()
        username = request.form["username"].strip()
        password = request.form["password"]

        error = None
        if not name or not room_number or not username or not password:
            error = "All fields are required."

        db = get_db()
        if error is None:
            try:
                db.execute(
                    "INSERT INTO student (name, room_number, username, password_hash) "
                    "VALUES (?, ?, ?, ?)",
                    (name, room_number, username, generate_password_hash(password)),
                )
                db.commit()
            except db.IntegrityError:
                error = f"Username {username} is already taken."
            else:
                flash("Registration successful. Please log in.")
                return redirect(url_for("student.login"))

        flash(error)

    return render_template("student/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db()
        error = None
        row = db.execute(
            "SELECT * FROM student WHERE username = ?", (username,)
        ).fetchone()

        if row is None or not check_password_hash(row["password_hash"], password):
            error = "Incorrect username or password."

        if error is None:
            session.clear()
            session["user_type"] = "student"
            session["user_id"] = row["id"]
            session["display_name"] = row["name"]
            return redirect(url_for("student.my_complaints"))

        flash(error)

    return render_template("student/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.choose_login"))


@bp.route("/complaints/new", methods=("GET", "POST"))
@login_required_student
def new_complaint():
    db = get_db()
    student = db.execute(
        "SELECT * FROM student WHERE id = ?", (session["user_id"],)
    ).fetchone()

    if request.method == "POST":
        category = request.form["category"]
        description = request.form["description"].strip()
        priority = request.form["priority"]
        room_number = request.form.get("room_number", "").strip() or student["room_number"]

        error = None
        if category not in CATEGORIES:
            error = "Invalid category."
        elif priority not in PRIORITIES:
            error = "Invalid priority."
        elif not description:
            error = "Description is required."

        if error is None:
            db.execute(
                "INSERT INTO complaint "
                "(student_id, category, description, room_number, status, priority, created_at, staff_notes) "
                "VALUES (?, ?, ?, ?, 'open', ?, ?, '')",
                (student["id"], category, description, room_number, priority, now_iso()),
            )
            db.commit()
            flash("Complaint submitted.")
            return redirect(url_for("student.my_complaints"))

        flash(error)

    return render_template(
        "student/new_complaint.html", categories=CATEGORIES, priorities=PRIORITIES, student=student
    )


@bp.route("/complaints")
@login_required_student
def my_complaints():
    db = get_db()
    complaints = db.execute(
        "SELECT * FROM complaint WHERE student_id = ? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    return render_template("student/my_complaints.html", complaints=complaints)
