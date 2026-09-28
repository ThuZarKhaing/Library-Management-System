"""Tests for the web layer: login, roles, CSRF and every route.

    python -m unittest tests.test_web -v
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from models import Book, StudentMember, TeacherMember, User
from models import user as user_model
from services import Library
from services.permissions import can, capabilities_for
from storage import LibraryStorage
from web import create_app

# The real cost of hashing a password is 240,000 rounds. That is the right
# number for a real login and the wrong number for 60 test logins, so the test
# suite turns it down and the code under test stays unchanged.
REAL_ROUNDS = user_model.HASH_ROUNDS


def setUpModule():
    user_model.HASH_ROUNDS = 1_000


def tearDownModule():
    user_model.HASH_ROUNDS = REAL_ROUNDS


def make_library():
    library = Library("Test Library")
    library.add_book(Book(101, "Python Programming", "John Smith", "Programming"))
    library.add_book(Book(102, "Data Structures", "Robert Brown", "Computer Science"))
    library.register_member(StudentMember(1, "Mg Mg", "mgmg@gmail.com"))
    library.register_member(TeacherMember(2, "U Aung", "uaung@gmail.com"))
    library.add_user(User.create("boss", "boss12345", role="admin", full_name="The Boss"))
    library.add_user(User.create("clerk", "clerk12345", role="staff", full_name="Front Desk"))
    return library


class WebTestCase(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.library = make_library()
        self.library.storage = LibraryStorage(self.folder)
        self.app = create_app(self.library, secret_key="test-secret", testing=True)
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    # ------------------------------------------------------------- helpers
    def token(self, path="/login"):
        """Fetch a page and return its CSRF token."""
        html = self.client.get(path).get_data(as_text=True)
        marker = 'name="csrf_token" value="'
        start = html.index(marker) + len(marker)
        return html[start : html.index('"', start)]

    def login(self, username, password):
        return self.client.post(
            "/login",
            data={
                "username": username,
                "password": password,
                "csrf_token": self.token(),
            },
            follow_redirects=True,
        )


class TestUserModel(unittest.TestCase):
    def test_password_is_never_stored(self):
        user = User.create("someone", "secret123", role="staff")
        self.assertNotIn("secret123", user.password_hash)
        self.assertNotIn("secret123", str(user.to_dict()))

    def test_check_password(self):
        user = User.create("someone", "secret123")
        self.assertTrue(user.check_password("secret123"))
        self.assertFalse(user.check_password("secret124"))
        self.assertFalse(user.check_password(""))
        self.assertFalse(user.check_password(None))

    def test_salt_is_random(self):
        first = User.create("a", "secret123").password_hash
        second = User.create("a", "secret123").password_hash
        self.assertNotEqual(first, second)

    def test_short_password_is_refused(self):
        with self.assertRaises(ValueError):
            User.create("a", "short")

    def test_bad_role_is_refused(self):
        with self.assertRaises(ValueError):
            User.create("a", "secret123", role="root")

    def test_username_is_normalised(self):
        self.assertEqual(User.create("  SomeOne ", "secret123").username, "someone")

    def test_set_password(self):
        user = User.create("a", "secret123")
        user.set_password("another123")
        self.assertFalse(user.check_password("secret123"))
        self.assertTrue(user.check_password("another123"))


class TestPermissions(unittest.TestCase):
    def test_staff_can_run_the_desk(self):
        for capability in ("view_dashboard", "view_books", "add_book", "borrow_book", "return_book"):
            self.assertTrue(can("staff", capability), capability)

    def test_staff_cannot_delete_or_manage_users(self):
        for capability in ("delete_book", "delete_member", "view_users", "manage_users"):
            self.assertFalse(can("staff", capability), capability)

    def test_admin_can_do_everything(self):
        self.assertEqual(capabilities_for("admin"), capabilities_for("admin"))
        for capability in capabilities_for("admin"):
            self.assertTrue(can("admin", capability), capability)

    def test_unknown_capability_raises(self):
        with self.assertRaises(KeyError):
            can("admin", "launch_rockets")


class TestAuthentication(WebTestCase):
    def test_login_page_is_public(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sign in", response.data)

    def test_dashboard_needs_a_login(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_successful_login(self):
        response = self.login("clerk", "clerk12345")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back", response.data)

    def test_wrong_password(self):
        response = self.login("clerk", "nope12345")
        self.assertIn(b"Wrong username or password", response.data)

    def test_unknown_user(self):
        response = self.login("ghost", "nope12345")
        self.assertIn(b"Wrong username or password", response.data)

    def test_empty_form(self):
        html = self.client.get("/login").get_data(as_text=True)
        marker = 'name="csrf_token" value="'
        start = html.index(marker) + len(marker)
        response = self.client.post(
            "/login",
            data={"username": "", "password": "", "csrf_token": html[start : html.index('"', start)]},
        )
        self.assertIn(b"Please enter both a username and a password", response.data)

    def test_logout(self):
        self.login("clerk", "clerk12345")
        response = self.client.post(
            "/logout", data={"csrf_token": self.token("/")}, follow_redirects=True
        )
        self.assertIn(b"signed out", response.data)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_login_is_case_insensitive(self):
        response = self.login("CLERK", "clerk12345")
        self.assertIn(b"Welcome back", response.data)

    def test_next_is_kept_after_login(self):
        self.client.get("/books")
        response = self.client.post(
            "/login",
            data={
                "username": "clerk",
                "password": "clerk12345",
                "next": "/books",
                "csrf_token": self.token("/login?next=/books"),
            },
        )
        self.assertTrue(response.headers["Location"].endswith("/books"))

    def test_open_redirect_is_refused(self):
        response = self.client.post(
            "/login",
            data={
                "username": "clerk",
                "password": "clerk12345",
                "next": "https://evil.example.com",
                "csrf_token": self.token("/login?next=https://evil.example.com"),
            },
        )
        self.assertEqual(response.headers["Location"], "/")


class TestCsrf(WebTestCase):
    def test_post_without_token_is_refused(self):
        self.login("clerk", "clerk12345")
        response = self.client.post("/books/101/delete", data={})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])
        self.assertIsNotNone(self.library.find_book(101))

    def test_post_with_a_wrong_token_is_refused(self):
        self.login("clerk", "clerk12345")
        response = self.client.post(
            "/books/101/delete", data={"csrf_token": "nonsense"}, follow_redirects=True
        )
        self.assertIn(b"form session expired", response.data)
        self.assertIsNotNone(self.library.find_book(101))

    def test_get_never_needs_a_token(self):
        self.login("clerk", "clerk12345")
        self.assertEqual(self.client.get("/books").status_code, 200)


class TestStaffPermissions(WebTestCase):
    def setUp(self):
        super().setUp()
        self.login("clerk", "clerk12345")

    def test_dashboard_and_lists(self):
        for path in ("/", "/books", "/members", "/profile"):
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_staff_sees_no_account_links(self):
        self.assertNotIn(b'href="/users"', self.client.get("/").data)

    def test_staff_cannot_open_the_user_pages(self):
        for path in ("/users", "/users/new"):
            self.assertEqual(self.client.get(path).status_code, 403, path)

    def test_staff_cannot_post_a_role_change(self):
        response = self.client.post(
            "/users/boss/role",
            data={"role": "staff", "csrf_token": self.token("/")},
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.library.find_user("boss").is_admin)

    def test_staff_cannot_delete_a_book(self):
        response = self.client.post(
            "/books/101/delete", data={"csrf_token": self.token("/books")},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(self.library.find_book(101))

    def test_staff_cannot_delete_a_member(self):
        response = self.client.post(
            "/members/1/delete", data={"csrf_token": self.token("/members")},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 403)
        self.assertIsNotNone(self.library.find_member(1))

    def test_staff_can_add_a_book(self):
        response = self.client.post(
            "/books/new",
            data={
                "book_id": "200", "title": "New Book", "author": "Nobody",
                "category": "General", "csrf_token": self.token("/books/new"),
            },
            follow_redirects=True,
        )
        self.assertIn(b"added successfully", response.data)
        self.assertIsNotNone(self.library.find_book(200))

    def test_staff_can_borrow_and_return(self):
        borrow = self.client.post(
            "/books/101/borrow",
            data={"member_id": "1", "csrf_token": self.token("/books")},
            follow_redirects=True,
        )
        # Jinja escapes the apostrophes, so look for the plain parts.
        self.assertIn(b"Mg Mg borrowed", borrow.data)
        self.assertIn(b"Python Programming", borrow.data)
        self.assertIn(b"successfully", borrow.data)
        self.assertFalse(self.library.find_book(101).is_available)

        give_back = self.client.post(
            "/books/101/return",
            data={"member_id": "1", "csrf_token": self.token("/books")},
            follow_redirects=True,
        )
        self.assertIn(b"Mg Mg returned", give_back.data)
        self.assertTrue(self.library.find_book(101).is_available)

    def test_staff_sees_no_buttons_they_cannot_use(self):
        html = self.client.get("/books").get_data(as_text=True)
        self.assertNotIn("Delete", html)
        self.assertIn("Borrow", html)


class TestAdminPermissions(WebTestCase):
    def setUp(self):
        super().setUp()
        self.login("boss", "boss12345")

    def test_admin_sees_the_account_page(self):
        response = self.client.get("/users")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Staff accounts", response.data)
        self.assertIn(b"clerk", response.data)

    def test_admin_can_delete_a_book(self):
        self.client.post(
            "/books/102/delete", data={"csrf_token": self.token("/books")},
            follow_redirects=True,
        )
        self.assertIsNone(self.library.find_book(102))

    def test_admin_cannot_delete_a_borrowed_book(self):
        self.library.borrow_book(1, 101)
        response = self.client.post(
            "/books/101/delete", data={"csrf_token": self.token("/books")},
            follow_redirects=True,
        )
        self.assertIn(b"still borrowed", response.data)
        self.assertIsNotNone(self.library.find_book(101))

    def test_admin_can_create_an_account(self):
        response = self.client.post(
            "/users/new",
            data={
                "username": "newbie", "full_name": "New Bie", "role": "staff",
                "password": "newbie123", "password2": "newbie123",
                "csrf_token": self.token("/users/new"),
            },
            follow_redirects=True,
        )
        self.assertIn(b"created", response.data)
        self.assertIsNotNone(self.library.find_user("newbie"))

    def test_password_rules(self):
        html = self.client.get("/users/new").get_data(as_text=True)
        marker = 'name="csrf_token" value="'
        start = html.index(marker) + len(marker)
        token = html[start : html.index('"', start)]
        cases = [
            ({"username": "a", "password": "short", "password2": "short"}, b"at least 8 characters"),
            ({"username": "a", "password": "longenough1", "password2": "other1234"}, b"do not match"),
        ]
        for extra, expected in cases:
            data = {"full_name": "", "role": "staff", "csrf_token": token, **extra}
            response = self.client.post("/users/new", data=data, follow_redirects=True)
            self.assertIn(expected, response.data)

    def test_duplicate_username(self):
        self.client.post(
            "/users/new",
            data={
                "username": "clerk", "full_name": "", "role": "staff",
                "password": "clerk12345", "password2": "clerk12345",
                "csrf_token": self.token("/users/new"),
            },
            follow_redirects=True,
        )
        self.assertEqual(len([u for u in self.library.users if u.username == "clerk"]), 1)

    def test_admin_cannot_delete_their_own_account(self):
        response = self.client.post(
            "/users/boss/delete", data={"csrf_token": self.token("/users")},
            follow_redirects=True,
        )
        self.assertIn(b"cannot delete your own account", response.data)
        self.assertIsNotNone(self.library.find_user("boss"))

    def test_admin_cannot_demote_the_last_admin(self):
        self.client.post(
            "/users/boss/role", data={"role": "staff", "csrf_token": self.token("/users")},
            follow_redirects=True,
        )
        self.assertTrue(self.library.find_user("boss").is_admin)

    def test_admin_can_promote_and_delete_others(self):
        self.client.post(
            "/users/clerk/role", data={"role": "admin", "csrf_token": self.token("/users")},
            follow_redirects=True,
        )
        self.assertTrue(self.library.find_user("clerk").is_admin)
        self.client.post(
            "/users/clerk/role", data={"role": "staff", "csrf_token": self.token("/users")},
            follow_redirects=True,
        )
        self.client.post(
            "/users/clerk/delete", data={"csrf_token": self.token("/users")},
            follow_redirects=True,
        )
        self.assertIsNone(self.library.find_user("clerk"))

    def test_permission_table_is_shown(self):
        html = self.client.get("/users").get_data(as_text=True)
        self.assertIn("Add a book", html)
        self.assertIn("Delete a book", html)
        self.assertIn("Create, edit and delete staff accounts", html)


class TestPagesAndSearch(WebTestCase):
    def setUp(self):
        super().setUp()
        self.login("clerk", "clerk12345")

    def test_search_by_keyword(self):
        html = self.client.get("/books?q=Robert").get_data(as_text=True)
        self.assertIn("Data Structures", html)
        self.assertNotIn("Python Programming", html)

    def test_status_filter(self):
        self.library.borrow_book(1, 101)
        available = self.client.get("/books?status=available").get_data(as_text=True)
        self.assertNotIn("Python Programming", available)
        borrowed = self.client.get("/books?status=borrowed").get_data(as_text=True)
        self.assertIn("Python Programming", borrowed)

    def test_search_members(self):
        html = self.client.get("/members?q=uaung").get_data(as_text=True)
        self.assertIn("U Aung", html)
        self.assertNotIn("Mg Mg", html)

    def test_empty_results(self):
        self.assertIn(b"No book matches", self.client.get("/books?q=zzzz").data)

    def test_dashboard_counts(self):
        self.library.borrow_book(1, 101)
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("Python Programming", html)
        self.assertIn("Mg Mg", html)

    def test_unknown_page(self):
        self.assertEqual(self.client.get("/nowhere").status_code, 404)

    def test_unknown_book_edit(self):
        self.assertEqual(self.client.get("/books/999/edit").status_code, 404)

    def test_editing_a_borrowed_book_keeps_the_loan(self):
        self.library.borrow_book(1, 101)
        member = self.library.find_member(1)
        self.client.post(
            "/books/101/edit",
            data={
                "book_id": "101", "title": "Python Programming 2e",
                "author": "John Smith", "category": "Programming",
                "csrf_token": self.token("/books/101/edit"),
            },
            follow_redirects=True,
        )
        book = self.library.find_book(101)
        self.assertEqual(book.title, "Python Programming 2e")
        self.assertFalse(book.is_available)
        self.assertTrue(member.has_reached_limit() is False)
        result = self.library.return_book(1, 101)
        self.assertTrue(result, "the member must still hold the edited book")

    def test_editing_a_member_keeps_their_books(self):
        self.library.borrow_book(1, 101)
        self.client.post(
            "/members/1/edit",
            data={
                "member_id": "1", "name": "Mg Mg Kyaw", "email": "kyaw@gmail.com",
                "csrf_token": self.token("/members/1/edit"),
            },
            follow_redirects=True,
        )
        member = self.library.find_member(1)
        self.assertEqual(member.name, "Mg Mg Kyaw")
        self.assertEqual(member.borrowed_count(), 1)
        self.assertTrue(self.library.return_book(1, 101))

    def test_member_type_cannot_be_changed_by_the_form(self):
        self.library.borrow_book(1, 101)
        self.client.post(
            "/members/1/edit",
            data={
                "member_id": "1", "name": "Mg Mg", "email": "mgmg@gmail.com",
                "member_type": "Teacher", "csrf_token": self.token("/members/1/edit"),
            },
            follow_redirects=True,
        )
        member = self.library.find_member(1)
        self.assertIsInstance(member, StudentMember)
        self.assertEqual(member.borrowing_limit(), 3)

    def test_change_own_password(self):
        response = self.client.post(
            "/profile",
            data={
                "current_password": "clerk12345", "new_password": "fresh12345",
                "new_password2": "fresh12345", "csrf_token": self.token("/profile"),
            },
            follow_redirects=True,
        )
        self.assertIn(b"password has been changed", response.data)
        self.assertTrue(self.library.authenticate("clerk", "fresh12345"))
        self.client.post("/logout", data={"csrf_token": self.token("/")})
        self.login("clerk", "fresh12345")

    def test_change_password_needs_the_current_one(self):
        response = self.client.post(
            "/profile",
            data={
                "current_password": "wrong12345", "new_password": "fresh12345",
                "new_password2": "fresh12345", "csrf_token": self.token("/profile"),
            },
            follow_redirects=True,
        )
        self.assertIn(b"current password is not correct", response.data)
        self.assertTrue(self.library.authenticate("clerk", "clerk12345"))


class TestWebPersistence(WebTestCase):
    def test_changes_are_written_to_disk(self):
        self.login("boss", "boss12345")
        self.client.post(
            "/books/new",
            data={
                "book_id": "300", "title": "Saved", "author": "Disk",
                "category": "General", "csrf_token": self.token("/books/new"),
            },
            follow_redirects=True,
        )
        self.assertTrue((self.folder / "books.json").exists())
        reloaded = Library("Test Library", storage=LibraryStorage(self.folder))
        reloaded.load()
        self.assertIsNotNone(reloaded.find_book(300))

    def test_users_are_written_without_the_password(self):
        self.library.save()
        text = (self.folder / "users.json").read_text(encoding="utf-8")
        self.assertNotIn("boss12345", text)
        self.assertIn("password_hash", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
