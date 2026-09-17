import sqlite3
from datetime import datetime

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS student (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    room_number TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS staff_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS complaint (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    room_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    priority TEXT NOT NULL DEFAULT 'medium',
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    staff_notes TEXT DEFAULT '',
    FOREIGN KEY (student_id) REFERENCES student (id)
);
"""

CATEGORIES = ["electrical", "plumbing", "furniture", "cleanliness", "internet", "other"]
STATUSES = ["open", "in_progress", "resolved", "rejected"]
PRIORITIES = ["low", "medium", "high"]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    seed_default_staff(db)
    db.commit()


def seed_default_staff(db):
    """Ensure there is always at least one staff/admin login available."""
    existing = db.execute(
        "SELECT id FROM staff_user WHERE username = ?", ("admin",)
    ).fetchone()
    if existing is None:
        db.execute(
            "INSERT INTO staff_user (name, role, username, password_hash) VALUES (?, ?, ?, ?)",
            ("Hostel Admin", "admin", "admin", generate_password_hash("admin123")),
        )


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command("init-db")
def init_db_command():
    """Clear existing data and re-create the tables."""
    init_db()
    click.echo("Initialized the database.")
