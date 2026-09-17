# Hostel Complaint Portal

[![Tests](https://github.com/pastbologanesh0101/hostel-complaint-portal/actions/workflows/tests.yml/badge.svg)](https://github.com/pastbologanesh0101/hostel-complaint-portal/actions/workflows/tests.yml)

A small Flask + SQLite web app for tracking maintenance complaints in a
student hostel/dormitory. Students file complaints (electrical, plumbing,
furniture, cleanliness, internet, other), track their own status, and staff
manage a queue of every complaint with filtering, status updates, and
simple resolution analytics.

## Features

- **Student accounts** — self-registration (name, room number, username,
  password), session-based login.
- **Submit complaints** — category, priority (low/medium/high), room number,
  free-text description.
- **My complaints** — a student only ever sees their own complaint history
  and current status.
- **Staff dashboard** — logged-in staff see every complaint, filterable by
  status, category, priority, and room number.
- **Status workflow** — staff move a complaint through
  `open → in_progress → resolved` (or `rejected`), and attach staff notes.
  Moving a complaint to `resolved` automatically stamps `resolved_at`;
  moving it back out of `resolved` (reopening it) clears `resolved_at`
  again, since the complaint is no longer actually resolved.
- **Analytics** — average resolution time (hours) across resolved
  complaints, complaint counts by category, and counts by status — handy
  for spotting recurring building issues (e.g. "plumbing" spiking in one
  wing).
- A default staff/admin account (`admin` / `admin123`) is seeded
  automatically so the staff side is usable out of the box. Change this in
  a real deployment.

## Tech

- Flask app-factory pattern (`create_app(testing=True)` uses a throwaway
  temp-file SQLite database so tests never touch your real data).
- Raw `sqlite3` (no ORM) with hashed passwords via `werkzeug.security`.
- Server-rendered Jinja2 templates + plain CSS, no JS framework.

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python run.py
# -> http://127.0.0.1:5000
```

A SQLite database is created automatically at `instance/hostel.sqlite` on
first run, along with the default staff account described above.

## Example usage

1. Open `http://127.0.0.1:5000`, choose **Student register**, create an
   account with your name, room number, username, and password.
2. Log in as that student and click **New complaint** — pick a category
   (e.g. `plumbing`), a priority, and describe the issue.
3. Track it under **My complaints** — status starts at `open`.
4. Log out, then log in as staff with `admin` / `admin123`.
5. Under **All complaints**, filter by status/category/room, open a
   complaint, change its status to `resolved`, and add a note. Reopening it
   later clears the resolution timestamp again.
6. Check **Analytics** for average resolution time and complaint counts by
   category/status.

## Running the tests

```bash
pip install -r requirements.txt pytest
pytest -v
```

The test suite (`tests/test_app.py`) covers: student registration/login,
submitting a complaint, students only seeing their own complaints, staff
seeing all complaints, filtering by status/category/room, `resolved_at`
being set on resolution and cleared on reopen, average-resolution-time and
count-by-category aggregation with known timestamps, and unauthenticated
access being rejected for both student and staff routes.

Tests run automatically on push/PR via GitHub Actions
(`.github/workflows/tests.yml`) against Python 3.11 and 3.12.

## Project layout

```
app/
  __init__.py       # create_app() app-factory
  db.py             # schema, get_db/init_db, default staff seed
  auth_helpers.py    # login_required_student / login_required_staff
  routes/
    auth.py         # landing page
    student.py      # register/login/submit/history
    staff.py        # login/list/update/analytics
  templates/        # Jinja2 templates
  static/style.css
tests/
  test_app.py
run.py
```

## License

MIT — see [LICENSE](LICENSE).
