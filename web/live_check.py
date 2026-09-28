"""End-to-end check of the running web dashboard.

    python web/live_check.py

Starts a real HTTP server on a spare port, drives it with real requests and
real cookies, prints one line per check, then shuts down and deletes the data
folder it made.  Your own ``data/`` files are never touched.

Use this after changing a template, a route or the CSS: the unit tests use
Flask's test client, this one uses the network.
"""

import http.cookiejar
import logging
import re
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Allow "python web/live_check.py" as well as "python -m web.live_check".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import Library  # noqa: E402
from storage import LibraryStorage  # noqa: E402
from web import create_app  # noqa: E402

logging.getLogger("werkzeug").setLevel(logging.ERROR)

HOST = "127.0.0.1"
PORT = 5099
BASE = f"http://{HOST}:{PORT}"

ADMIN = ("admin", "admin12345")
STAFF = ("staff", "staff12345")

TOKEN_PATTERN = re.compile(r'name="csrf_token" value="([^"]+)"')
REDIRECTS = (301, 302, 303, 307, 308)

passed = 0
failed = 0


# ------------------------------------------------------------------- the http
class Browser:
    """A very small browser: keeps cookies, does not follow redirects."""

    def __init__(self, base):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect()
        )

    def get(self, path):
        status, _location, body = self._send(urllib.request.Request(self.base + path))
        return status, body

    def post(self, path, fields, token_from="/"):
        """POST with a fresh CSRF token read from ``token_from``."""
        status, _location, body = self.post_raw(path, fields, token_from)
        return status, body

    def post_raw(self, path, fields, token_from="/"):
        """Same, but also gives the Location header of a redirect.

        ``token_from=None`` deliberately sends no token at all.
        """
        data = dict(fields)
        if token_from is not None:
            data["csrf_token"] = self.token(token_from)
        body = urllib.parse.urlencode(data).encode()
        request = urllib.request.Request(self.base + path, data=body, method="POST")
        return self._send(request)

    def post_follow(self, path, fields, token_from="/"):
        """POST, then follow the redirect, so flash messages are visible."""
        status, location, body = self.post_raw(path, fields, token_from)
        if status in REDIRECTS and location:
            return self.get(location)
        return status, body

    def _send(self, request):
        try:
            with self.opener.open(request, timeout=10) as response:
                return (
                    response.status,
                    response.headers.get("Location"),
                    response.read().decode("utf-8", "replace"),
                )
        except urllib.error.HTTPError as error:
            return (
                error.code,
                error.headers.get("Location"),
                error.read().decode("utf-8", "replace"),
            )

    def token(self, path="/"):
        _status, body = self.get(path)
        match = TOKEN_PATTERN.search(body)
        if not match:
            raise AssertionError(f"no CSRF token found on {path}")
        return match.group(1)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def check(label, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}  {detail}")


def section(title):
    print(f"\n{title}")


# ----------------------------------------------------------------- the checks
def run(app):
    print("=" * 62)
    print("Web dashboard end-to-end check")
    print("=" * 62)

    browser = Browser(BASE)

    section("1. Public pages")
    status, body = browser.get("/login")
    check("login page loads", status == 200 and "csrf_token" in body, status)
    status, _ = browser.get("/static/style.css")
    check("stylesheet is served", status == 200, status)
    status, _ = browser.get("/nowhere")
    check("unknown page gives 404", status == 404, status)

    section("2. Closed until you sign in")
    status, _ = browser.get("/")
    check("dashboard redirects to login", status == 302, status)
    status, _ = browser.get("/books")
    check("books redirect to login", status == 302, status)
    status, _ = browser.get("/users")
    check("staff accounts redirect to login", status == 302, status)

    section("3. Signing in")
    status, body = browser.post(
        "/login", {"username": "admin", "password": "wrong-one"}, token_from="/login"
    )
    check("wrong password is refused", "Wrong username or password" in body)
    status, _location, _body = browser.post_raw(
        "/login", {"username": "admin", "password": "admin12345"}, token_from=None
    )
    check("POST without a CSRF token is refused", status == 302, status)

    browser.post_follow("/login", dict(zip(("username", "password"), STAFF)), "/login")
    status, body = browser.get("/")
    check("staff can sign in", status == 200 and "Dashboard" in body, status)

    section("4. What a staff account may not do")
    check("no link to the accounts page", 'href="/users"' not in body)
    check("no delete button on the dashboard", "Delete" not in body)
    status, _ = browser.get("/users")
    check("accounts page is 403", status == 403, status)
    status, _ = browser.get("/users/new")
    check("new account page is 403", status == 403, status)
    status, _ = browser.post("/books/101/delete", {})
    check("cannot delete a book", status == 403, status)
    status, _ = browser.post("/members/1/delete", {})
    check("cannot delete a member", status == 403, status)
    status, _ = browser.post("/users/admin/role", {"role": "staff"})
    check("cannot change a role", status == 403, status)

    section("5. What a staff account can do")
    status, body = browser.post_follow(
        "/books/new",
        {"book_id": "900", "title": "Checked Live", "author": "The Script", "category": "Testing"},
    )
    check("adding a book works", status == 200 and "added successfully" in body)
    status, body = browser.get("/books?q=Checked")
    check("the new book is listed", "Checked Live" in body)

    status, body = browser.post_follow("/books/101/borrow", {"member_id": "1"})
    check("borrowing works", status == 200 and "borrowed" in body)
    status, body = browser.get("/books?status=borrowed")
    check("the book shows as on loan", "On loan" in body)
    status, body = browser.post_follow("/books/101/return", {"member_id": "1"})
    check("returning works", status == 200 and "returned" in body)
    status, body = browser.get("/books?status=available")
    check("the book is available again", "Available" in body)

    section("6. Signing out and in as an administrator")
    browser.post_follow("/logout", {})
    status, _ = browser.get("/")
    check("signing out locks the pages", status == 302, status)

    browser.post_follow("/login", dict(zip(("username", "password"), ADMIN)), "/login")
    status, body = browser.get("/")
    check("admin dashboard loads", status == 200, status)
    check("accounts link is visible", 'href="/users"' in body)
    status, body = browser.get("/users")
    check("accounts page opens", status == 200 and "admin" in body, status)

    section("7. Administrator powers")
    status, body = browser.post_follow("/books/900/delete", {})
    check("admin can delete a book", status == 200 and "removed successfully" in body)
    status, body = browser.post_follow(
        "/users/new",
        {
            "username": "temp_clerk", "full_name": "Temp", "role": "staff",
            "password": "temp12345", "password2": "temp12345",
        },
    )
    check("admin can create an account", status == 200 and "created" in body)
    status, body = browser.post_follow("/users/temp_clerk/role", {"role": "admin"})
    check("admin can promote someone", status == 200 and "now a admin" in body)
    status, body = browser.post_follow("/users/admin/delete", {})
    check("admin cannot delete their own account", "cannot delete your own" in body)
    status, body = browser.post_follow("/users/temp_clerk/delete", {})
    check("admin can delete that account", status == 200 and "deleted" in body)

    section("8. Password rules")
    status, body = browser.post_follow(
        "/users/new",
        {"username": "weak", "full_name": "", "role": "staff",
         "password": "short", "password2": "short"},
    )
    check("short passwords are refused", "at least 8 characters" in body)
    status, body = browser.post_follow(
        "/users/new",
        {"username": "mismatch", "full_name": "", "role": "staff",
         "password": "longenough1", "password2": "different123"},
    )
    check("mismatched passwords are refused", "do not match" in body)
    status, body = browser.post_follow(
        "/profile",
        {"current_password": "admin12345", "new_password": "brandnew123",
         "new_password2": "brandnew123"},
    )
    check("admin can change their own password", "password has been changed" in body)
    browser.post_follow("/logout", {})
    browser.post_follow(
        "/login", {"username": "admin", "password": "brandnew123"}, "/login"
    )
    status, body = browser.get("/")
    check("the new password works", status == 200, status)

    print("\n" + "=" * 62)
    print(f"{passed} passed, {failed} failed")
    print("=" * 62)
    return failed


# ---------------------------------------------------------------------- server
def main():
    folder = Path(tempfile.mkdtemp(prefix="lms_live_check_"))
    print(f"Temporary data folder: {folder}\n")

    library = Library("Live Check Library", storage=LibraryStorage(folder)).load()
    app = create_app(library, secret_key="live-check-secret")

    try:
        from werkzeug.serving import make_server
    except ImportError:
        print("Flask is not installed. Run:  pip install -r requirements.txt")
        return 1

    server = make_server(HOST, PORT, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Server listening on {BASE}")

    failures = 0
    try:
        failures = run(app)
    except Exception as error:
        print(f"\n  ERROR  {type(error).__name__}: {error}")
        failures += 1
    finally:
        server.shutdown()
        thread.join(timeout=5)
        shutil.rmtree(folder, ignore_errors=True)
        print(f"Server stopped. Temporary folder deleted. ({library.name} untouched)")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
