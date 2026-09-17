import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from app import create_app
from app.db import get_db, now_iso


@pytest.fixture
def app():
    application = create_app(testing=True)
    yield application
    db_path = getattr(application, "_tmp_db_path", None)
    if db_path and os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


# ---- helpers -----------------------------------------------------------

def register_student(client, username="alice", password="pw12345", name="Alice", room="101"):
    return client.post(
        "/student/register",
        data={"name": name, "room_number": room, "username": username, "password": password},
        follow_redirects=True,
    )


def login_student(client, username="alice", password="pw12345"):
    return client.post(
        "/student/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def login_staff(client, username="admin", password="admin123"):
    return client.post(
        "/staff/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def submit_complaint(client, category="plumbing", description="Leaking tap", priority="high", room=""):
    return client.post(
        "/student/complaints/new",
        data={
            "category": category,
            "description": description,
            "priority": priority,
            "room_number": room,
        },
        follow_redirects=True,
    )


def insert_complaint(app, student_id, category="plumbing", status="open", priority="medium",
                      room="101", created_at=None, resolved_at=None, description="issue"):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO complaint "
            "(student_id, category, description, room_number, status, priority, created_at, resolved_at, staff_notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, '')",
            (student_id, category, description, room, status, priority,
             created_at or now_iso(), resolved_at),
        )
        db.commit()


def get_student_id(app, username):
    with app.app_context():
        db = get_db()
        row = db.execute("SELECT id FROM student WHERE username = ?", (username,)).fetchone()
        return row["id"]


# ---- tests --------------------------------------------------------------

def test_student_register_and_login(client):
    register_student(client, username="alice")
    resp = login_student(client, username="alice")
    assert resp.status_code == 200
    assert b"My complaints" in resp.data


def test_student_submit_complaint(app, client):
    register_student(client, username="alice")
    login_student(client, username="alice")
    resp = submit_complaint(client, category="electrical", description="Fan not working")
    assert resp.status_code == 200
    assert b"Fan not working" in resp.data

    student_id = get_student_id(app, "alice")
    with app.app_context():
        db = get_db()
        rows = db.execute("SELECT * FROM complaint WHERE student_id = ?", (student_id,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "open"
    assert rows[0]["category"] == "electrical"


def test_student_sees_only_own_complaints(app, client):
    register_student(client, username="alice", room="101")
    register_student(client, username="bob", name="Bob", room="202")

    login_student(client, username="alice")
    submit_complaint(client, description="Alice's broken window")
    client.get("/student/logout")

    login_student(client, username="bob")
    submit_complaint(client, description="Bob's clogged sink")
    resp = client.get("/student/complaints")

    assert b"Bob&#39;s clogged sink" in resp.data or b"Bob's clogged sink" in resp.data
    assert b"Alice" not in resp.data
    assert b"broken window" not in resp.data


def test_staff_sees_all_complaints(app, client):
    register_student(client, username="alice", room="101")
    register_student(client, username="bob", name="Bob", room="202")
    login_student(client, username="alice")
    submit_complaint(client, description="Alice issue one")
    client.get("/student/logout")
    login_student(client, username="bob")
    submit_complaint(client, description="Bob issue one")
    client.get("/student/logout")

    login_staff(client)
    resp = client.get("/staff/complaints")
    assert b"Alice issue one" in resp.data
    assert b"Bob issue one" in resp.data


def test_staff_filter_by_status(app, client):
    register_student(client, username="alice", room="101")
    sid = get_student_id(app, "alice")
    insert_complaint(app, sid, status="open", description="open one")
    insert_complaint(app, sid, status="resolved", description="resolved one",
                      resolved_at=now_iso())

    login_staff(client)
    resp = client.get("/staff/complaints?status=resolved")
    assert b"resolved one" in resp.data
    assert b"open one" not in resp.data


def test_staff_filter_by_category(app, client):
    register_student(client, username="alice", room="101")
    sid = get_student_id(app, "alice")
    insert_complaint(app, sid, category="internet", description="wifi down")
    insert_complaint(app, sid, category="furniture", description="broken chair")

    login_staff(client)
    resp = client.get("/staff/complaints?category=internet")
    assert b"wifi down" in resp.data
    assert b"broken chair" not in resp.data


def test_staff_filter_by_room(app, client):
    register_student(client, username="alice", room="101")
    sid = get_student_id(app, "alice")
    insert_complaint(app, sid, room="101", description="room 101 issue")
    insert_complaint(app, sid, room="303", description="room 303 issue")

    login_staff(client)
    resp = client.get("/staff/complaints?room_number=303")
    assert b"room 303 issue" in resp.data
    assert b"room 101 issue" not in resp.data


def test_status_update_sets_resolved_at(app, client):
    register_student(client, username="alice", room="101")
    sid = get_student_id(app, "alice")
    insert_complaint(app, sid, status="open", description="needs fixing")

    with app.app_context():
        db = get_db()
        complaint_id = db.execute("SELECT id FROM complaint").fetchone()["id"]

    login_staff(client)
    client.post(
        f"/staff/complaints/{complaint_id}",
        data={"status": "resolved", "staff_notes": "fixed it"},
        follow_redirects=True,
    )

    with app.app_context():
        db = get_db()
        row = db.execute("SELECT * FROM complaint WHERE id = ?", (complaint_id,)).fetchone()
    assert row["status"] == "resolved"
    assert row["resolved_at"] is not None


def test_reopen_clears_resolved_at(app, client):
    register_student(client, username="alice", room="101")
    sid = get_student_id(app, "alice")
    insert_complaint(app, sid, status="resolved", description="was fixed", resolved_at=now_iso())

    with app.app_context():
        db = get_db()
        complaint_id = db.execute("SELECT id FROM complaint").fetchone()["id"]

    login_staff(client)
    # Reopen: move it back to in_progress.
    client.post(
        f"/staff/complaints/{complaint_id}",
        data={"status": "in_progress", "staff_notes": "reopened, still broken"},
        follow_redirects=True,
    )

    with app.app_context():
        db = get_db()
        row = db.execute("SELECT * FROM complaint WHERE id = ?", (complaint_id,)).fetchone()
    assert row["status"] == "in_progress"
    assert row["resolved_at"] is None


def test_average_resolution_time_computed_correctly(app, client):
    register_student(client, username="alice", room="101")
    sid = get_student_id(app, "alice")

    # Complaint 1: resolved in exactly 2 hours.
    insert_complaint(
        app, sid, status="resolved", description="two hour fix",
        created_at="2026-01-01T10:00:00", resolved_at="2026-01-01T12:00:00",
    )
    # Complaint 2: resolved in exactly 4 hours.
    insert_complaint(
        app, sid, status="resolved", description="four hour fix",
        created_at="2026-01-01T10:00:00", resolved_at="2026-01-01T14:00:00",
    )
    # An unresolved complaint should NOT be counted.
    insert_complaint(app, sid, status="open", description="still open")

    login_staff(client)
    resp = client.get("/staff/analytics")
    # Average of 2h and 4h = 3.0 hours.
    assert b"3.0 hours" in resp.data
    assert b"Based on 2 resolved complaint" in resp.data


def test_count_by_category_aggregation(app, client):
    register_student(client, username="alice", room="101")
    sid = get_student_id(app, "alice")
    insert_complaint(app, sid, category="plumbing", description="a")
    insert_complaint(app, sid, category="plumbing", description="b")
    insert_complaint(app, sid, category="electrical", description="c")

    login_staff(client)
    resp = client.get("/staff/analytics")
    html = resp.data.decode()

    assert "plumbing" in html
    assert "electrical" in html
    # crude but effective: the plumbing row should show a count of 2
    plumbing_idx = html.index("plumbing")
    snippet = html[plumbing_idx:plumbing_idx + 200]
    assert ">2<" in snippet


def test_unauthenticated_staff_route_rejected(client):
    resp = client.get("/staff/complaints")
    assert resp.status_code == 401

    resp2 = client.get("/staff/analytics")
    assert resp2.status_code == 401


def test_unauthenticated_student_route_rejected(client):
    resp = client.get("/student/complaints")
    assert resp.status_code == 401

    resp2 = client.get("/student/complaints/new")
    assert resp2.status_code == 401
