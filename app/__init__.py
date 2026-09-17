import os
import tempfile

from flask import Flask, redirect, url_for

from . import db as db_module


def create_app(testing=False, database=None, instance_path=None):
    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)
    app.config.from_mapping(
        SECRET_KEY="dev-secret-key-change-in-production",
        DATABASE=database,
    )

    if testing:
        app.config.update(TESTING=True)
        if database is None:
            # A real (temp) file-backed SQLite DB so every request/connection
            # within the test sees the same data, unlike a bare ':memory:' DB
            # which resets per-connection.
            fd, path = tempfile.mkstemp(suffix=".sqlite")
            os.close(fd)
            app.config["DATABASE"] = path
            app._tmp_db_path = path
    else:
        if app.config["DATABASE"] is None:
            try:
                os.makedirs(app.instance_path)
            except OSError:
                pass
            app.config["DATABASE"] = os.path.join(app.instance_path, "hostel.sqlite")

    db_module.init_app(app)

    from .routes import auth, student, staff

    app.register_blueprint(auth.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(staff.bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.choose_login"))

    with app.app_context():
        db_module.init_db()

    return app
