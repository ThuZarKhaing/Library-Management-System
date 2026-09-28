"""Who is allowed in, and how a request proves it came from our own form.

Kept apart from ``app.py`` so that the routes and the application factory can
both use it without importing each other.
"""

import hmac
import secrets
from functools import wraps

from flask import (
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from services import can
from services.permissions import CAPABILITY_LABELS

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FORM_FIELD = "csrf_token"
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


def csrf_token():
    """The token for this session, created the first time it is needed."""
    if CSRF_SESSION_KEY not in session:
        session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]


def csrf_is_valid():
    """True when the request carries the token belonging to this session."""
    expected = session.get(CSRF_SESSION_KEY, "")
    given = request.form.get(CSRF_FORM_FIELD) or request.headers.get("X-CSRF-Token", "")
    if not expected or not given:
        return False
    return hmac.compare_digest(expected, given)


def reject_without_csrf():
    """Stop a POST that has no valid token and send the user back to the form."""
    if request.method in SAFE_METHODS:
        return None
    if csrf_is_valid():
        return None
    flash("Your form session expired. Please try again.", "error")
    return redirect(url_for("views.login", next=request.full_path))


def login_required(view):
    """Send anonymous visitors to the login page."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.get("user") is None:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("views.login", next=request.full_path))
        return view(*args, **kwargs)

    return wrapper


def capability_required(capability):
    """Allow the view only for the roles that hold ``capability``."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            if not can(g.user.role, capability):
                return render_template(
                    "error.html",
                    code=403,
                    title="Not allowed",
                    message=(
                        f"A {g.user.role_label.lower()} account cannot "
                        f"{CAPABILITY_LABELS[capability].lower()}."
                    ),
                ), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(view):
    return capability_required("manage_users")(view)
