"""The web application factory.

``create_app`` wires Flask to the same :class:`Library` object the console and
the desktop app use.  Nothing about the rules lives here: routes call the
library, and the library decides what is allowed to happen.
"""

import os
import secrets

from flask import Flask, g, render_template, session

from services import Library, can
from services.permissions import CAPABILITY_LABELS, matrix
from storage import LibraryStorage
from . import views
from .security import csrf_token, reject_without_csrf


def create_app(library=None, secret_key=None, testing=False):
    """Build the Flask app.

    :param library: an existing Library; one is loaded from disk if omitted.
    :param secret_key: signs the session cookie. Read from SECRET_KEY when None.
    :param testing: turns on the behaviour the test suite relies on.
    """
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secret_key or os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=256 * 1024,
        TEMPLATES_AUTO_RELOAD=testing,
    )
    app.testing = testing

    if library is None:
        library = Library("My School Library", storage=LibraryStorage()).load()
    app.library = library

    app.register_blueprint(views.blueprint)
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.context_processor
    def inject_globals():
        """Values every template can use without being passed in."""
        return {
            "current_user": getattr(g, "user", None),
            "can": can,
            "capability_labels": CAPABILITY_LABELS,
            "capability_roles": matrix(),
            "library_name": app.library.name,
        }

    @app.template_filter("date")
    def format_date(value):
        return value.strftime("%d %b %Y") if hasattr(value, "strftime") else value

    @app.before_request
    def load_logged_in_user():
        """Put the signed-in account on ``g`` so the templates can use it."""
        username = session.get("username")
        g.user = app.library.find_user(username) if username else None

    @app.before_request
    def check_csrf_token():
        return reject_without_csrf()

    @app.errorhandler(403)
    def forbidden(_error):
        return (
            render_template(
                "error.html",
                code=403,
                title="Not allowed",
                message="Your account does not have permission to do that.",
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_template(
                "error.html",
                code=404,
                title="Page not found",
                message="That page does not exist.",
            ),
            404,
        )

    @app.errorhandler(500)
    def server_error(_error):
        app.library.save()
        return (
            render_template(
                "error.html",
                code=500,
                title="Something went wrong",
                message="The problem has been written to the log.",
            ),
            500,
        )

    return app
