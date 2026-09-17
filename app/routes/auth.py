from flask import Blueprint, render_template

bp = Blueprint("auth", __name__)


@bp.route("/login")
def choose_login():
    """Landing page letting a visitor pick student or staff login."""
    return render_template("choose_login.html")
