from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from ..auth_helpers import login_required_staff
from ..db import CATEGORIES, PRIORITIES, STATUSES, get_db, now_iso

bp = Blueprint("staff", __name__, url_prefix="/staff")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db()
        error = None
        row = db.execute(
            "SELECT * FROM staff_user WHERE username = ?", (username,)
        ).fetchone()

        if row is None or not check_password_hash(row["password_hash"], password):
            error = "Incorrect username or password."

        if error is None:
            session.clear()
            session["user_type"] = "staff"
            session["user_id"] = row["id"]
            session["display_name"] = row["name"]
            return redirect(url_for("staff.list_complaints"))

        flash(error)

    return render_template("staff/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.choose_login"))


@bp.route("/complaints")
@login_required_staff
def list_complaints():
    db = get_db()

    status = request.args.get("status", "")
    category = request.args.get("category", "")
    priority = request.args.get("priority", "")
    room_number = request.args.get("room_number", "")

    query = (
        "SELECT complaint.*, student.name AS student_name "
        "FROM complaint JOIN student ON complaint.student_id = student.id "
        "WHERE 1=1"
    )
    params = []
    if status:
        query += " AND complaint.status = ?"
        params.append(status)
    if category:
        query += " AND complaint.category = ?"
        params.append(category)
    if priority:
        query += " AND complaint.priority = ?"
        params.append(priority)
    if room_number:
        query += " AND complaint.room_number = ?"
        params.append(room_number)
    query += " ORDER BY complaint.created_at DESC"

    complaints = db.execute(query, params).fetchall()

    return render_template(
        "staff/list_complaints.html",
        complaints=complaints,
        statuses=STATUSES,
        categories=CATEGORIES,
        priorities=PRIORITIES,
        filters={
            "status": status,
            "category": category,
            "priority": priority,
            "room_number": room_number,
        },
    )


@bp.route("/complaints/<int:complaint_id>", methods=("GET", "POST"))
@login_required_staff
def update_complaint(complaint_id):
    db = get_db()
    complaint = db.execute(
        "SELECT complaint.*, student.name AS student_name "
        "FROM complaint JOIN student ON complaint.student_id = student.id "
        "WHERE complaint.id = ?",
        (complaint_id,),
    ).fetchone()

    if complaint is None:
        flash("Complaint not found.")
        return redirect(url_for("staff.list_complaints"))

    if request.method == "POST":
        new_status = request.form["status"]
        staff_notes = request.form.get("staff_notes", "").strip()

        if new_status not in STATUSES:
            flash("Invalid status.")
        else:
            # Moving into 'resolved' stamps resolved_at automatically.
            # Moving back out of 'resolved' (reopening) clears it again,
            # since a complaint that is open/in_progress/rejected again
            # hasn't actually been resolved.
            if new_status == "resolved" and complaint["status"] != "resolved":
                resolved_at = now_iso()
            elif new_status != "resolved":
                resolved_at = None
            else:
                resolved_at = complaint["resolved_at"]

            db.execute(
                "UPDATE complaint SET status = ?, staff_notes = ?, resolved_at = ? WHERE id = ?",
                (new_status, staff_notes, resolved_at, complaint_id),
            )
            db.commit()
            flash("Complaint updated.")
            return redirect(url_for("staff.list_complaints"))

    return render_template(
        "staff/update_complaint.html", complaint=complaint, statuses=STATUSES
    )


@bp.route("/analytics")
@login_required_staff
def analytics():
    db = get_db()

    resolved_rows = db.execute(
        "SELECT created_at, resolved_at FROM complaint "
        "WHERE status = 'resolved' AND resolved_at IS NOT NULL"
    ).fetchall()

    avg_resolution_hours = None
    if resolved_rows:
        total_seconds = 0.0
        for row in resolved_rows:
            created = datetime.fromisoformat(row["created_at"])
            resolved = datetime.fromisoformat(row["resolved_at"])
            total_seconds += (resolved - created).total_seconds()
        avg_resolution_hours = round((total_seconds / len(resolved_rows)) / 3600, 2)

    by_category = db.execute(
        "SELECT category, COUNT(*) AS count FROM complaint GROUP BY category ORDER BY category"
    ).fetchall()
    by_status = db.execute(
        "SELECT status, COUNT(*) AS count FROM complaint GROUP BY status ORDER BY status"
    ).fetchall()

    return render_template(
        "staff/analytics.html",
        avg_resolution_hours=avg_resolution_hours,
        resolved_count=len(resolved_rows),
        by_category=by_category,
        by_status=by_status,
    )
