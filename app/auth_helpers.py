import functools

from flask import abort, session


def login_required_student(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_type") != "student" or "user_id" not in session:
            abort(401)
        return view(**kwargs)

    return wrapped_view


def login_required_staff(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_type") != "staff" or "user_id" not in session:
            abort(401)
        return view(**kwargs)

    return wrapped_view
