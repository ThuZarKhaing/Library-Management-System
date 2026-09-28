"""Every page of the web dashboard.

Each route does the same four things: check the role, read the form, call the
Library, then redirect with a message.  A route never decides what is allowed -
the Library does.
"""

from urllib.parse import urlparse

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models import Book, StudentMember, TeacherMember, User, ValidationError
from .security import admin_required, capability_required, login_required

blueprint = Blueprint("views", __name__)

MEMBER_CLASSES = {"Student": StudentMember, "Teacher": TeacherMember}
BOOK_STATUS_FILTERS = ("all", "available", "borrowed")


def library():
    return current_app.library


def safe_next(target, fallback):
    """Only allow redirects that stay on this site."""
    if not target:
        return fallback
    parts = urlparse(target)
    if parts.scheme or parts.netloc or not target.startswith("/"):
        return fallback
    return target


def value(name, default=""):
    return request.form.get(name, default).strip()


def fail(message):
    flash(message, "error")
    return False


def holder_of(book):
    """The member who has this book on loan, if anyone."""
    for member in library().members:
        if member.has_borrowed(book):
            return member
    return None


# ----------------------------------------------------------------------- login
@blueprint.route("/login", methods=["GET", "POST"])
def login():
    if g.get("user") is not None:
        return redirect(url_for("views.dashboard"))
    if request.method == "POST":
        username = value("username").lower()
        password = request.form.get("password", "")
        if not username or not password:
            fail("Please enter both a username and a password.")
        elif library().authenticate(username, password) is None:
            fail("Wrong username or password.")
        else:
            session.clear()
            session["username"] = username
            flash("Welcome back.", "success")
            return redirect(safe_next(value("next"), url_for("views.dashboard")))
    return render_template(
        "login.html", next=value("next") or request.args.get("next", "")
    )


@blueprint.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("views.login"))


# ------------------------------------------------------------------- dashboard
@blueprint.route("/")
@capability_required("view_dashboard")
def dashboard():
    the_library = library()
    on_loan = [(book, holder_of(book)) for book in the_library.get_borrowed_books()]
    return render_template(
        "dashboard.html",
        stats=the_library.statistics(),
        on_loan=on_loan[:8],
        staff_count=len(the_library.users),
    )


# ------------------------------------------------------------------------ books
@blueprint.route("/books")
@capability_required("view_books")
def books():
    the_library = library()
    keyword = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    if status not in BOOK_STATUS_FILTERS:
        status = "all"

    rows = the_library.find_books(keyword)
    if status == "available":
        rows = [book for book in rows if book.is_available]
    elif status == "borrowed":
        rows = [book for book in rows if not book.is_available]

    return render_template(
        "books.html",
        rows=rows,
        holders={book: holder_of(book) for book in rows},
        keyword=keyword,
        status=status,
        members=the_library.members,
        next_book_id=the_library.next_book_id(),
    )


@blueprint.route("/books/new", methods=["GET", "POST"])
@capability_required("add_book")
def new_book():
    form = {
        "book_id": str(library().next_book_id()),
        "title": "",
        "author": "",
        "category": "General",
    }
    if request.method == "POST":
        form = {
            "book_id": value("book_id"),
            "title": value("title"),
            "author": value("author"),
            "category": value("category") or "General",
        }
        try:
            book = Book(form["book_id"], form["title"], form["author"], form["category"])
        except (ValidationError, TypeError) as error:
            fail(str(error))
        else:
            result = library().add_book(book)
            flash(result.message, "success" if result else "error")
            if result:
                return redirect(url_for("views.books"))
    return render_template(
        "book_form.html",
        form=form,
        action=url_for("views.new_book"),
        title="Add a book",
        submit="Add book",
    )


@blueprint.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@capability_required("edit_book")
def edit_book(book_id):
    the_library = library()
    book = the_library.find_book(book_id) or abort(404)
    form = {
        "book_id": str(book.book_id),
        "title": book.title,
        "author": book.author,
        "category": book.category,
    }
    if request.method == "POST":
        form = {
            "book_id": value("book_id"),
            "title": value("title"),
            "author": value("author"),
            "category": value("category") or "General",
        }
        try:
            updated = Book(
                form["book_id"], form["title"], form["author"], form["category"]
            )
        except (ValidationError, TypeError) as error:
            fail(str(error))
        else:
            clash = the_library.find_book(updated.book_id)
            if clash is not None and clash is not book:
                fail(f"A book with ID {updated.book_id} already exists.")
            else:
                book.update(
                    book_id=updated.book_id,
                    title=updated.title,
                    author=updated.author,
                    category=updated.category,
                )
                the_library.save()
                flash(f"'{book.title}' updated.", "success")
                return redirect(url_for("views.books"))
    return render_template(
        "book_form.html",
        form=form,
        action=url_for("views.edit_book", book_id=book_id),
        title="Edit book",
        submit="Save changes",
    )


@blueprint.route("/books/<int:book_id>/delete", methods=["POST"])
@capability_required("delete_book")
def delete_book(book_id):
    result = library().remove_book(book_id)
    flash(result.message, "success" if result else "error")
    return redirect(url_for("views.books"))


@blueprint.route("/books/<int:book_id>/borrow", methods=["POST"])
@capability_required("borrow_book")
def borrow_book(book_id):
    result = library().borrow_book(value("member_id"), book_id)
    flash(result.message, "success" if result else "error")
    return redirect(request.referrer or url_for("views.books"))


@blueprint.route("/books/<int:book_id>/return", methods=["POST"])
@capability_required("return_book")
def return_book(book_id):
    result = library().return_book(value("member_id"), book_id)
    flash(result.message, "success" if result else "error")
    return redirect(request.referrer or url_for("views.books"))


# --------------------------------------------------------------------- members
@blueprint.route("/members")
@capability_required("view_members")
def members():
    keyword = request.args.get("q", "").strip().lower()
    rows = library().members
    if keyword:
        rows = [
            member
            for member in rows
            if keyword in member.name.lower() or keyword in member.email.lower()
        ]
    return render_template(
        "members.html",
        rows=rows,
        keyword=keyword,
        next_member_id=library().next_member_id(),
    )


@blueprint.route("/members/new", methods=["GET", "POST"])
@capability_required("add_member")
def new_member():
    form = {
        "member_id": str(library().next_member_id()),
        "name": "",
        "email": "",
        "member_type": "Student",
    }
    if request.method == "POST":
        form = {
            "member_id": value("member_id"),
            "name": value("name"),
            "email": value("email"),
            "member_type": value("member_type", "Student"),
        }
        try:
            member = build_member(form)
        except (ValidationError, TypeError, ValueError) as error:
            fail(str(error))
        else:
            result = library().register_member(member)
            flash(result.message, "success" if result else "error")
            if result:
                return redirect(url_for("views.members"))
    return render_template(
        "member_form.html",
        form=form,
        action=url_for("views.new_member"),
        title="Register a member",
        submit="Register member",
    )


@blueprint.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
@capability_required("edit_member")
def edit_member(member_id):
    the_library = library()
    member = the_library.find_member(member_id) or abort(404)
    form = {
        "member_id": str(member.member_id),
        "name": member.name,
        "email": member.email,
        "member_type": member.member_type(),
    }
    if request.method == "POST":
        # The type is fixed: it decides the class, and a student and a teacher
        # are not interchangeable once books are on loan.
        form.update(
            member_id=value("member_id"),
            name=value("name"),
            email=value("email"),
        )
        try:
            checked = build_member({**form, "member_type": member.member_type()})
        except (ValidationError, TypeError, ValueError) as error:
            fail(str(error))
        else:
            clash = the_library.find_member(checked.member_id)
            if clash is not None and clash is not member:
                fail(f"A member with ID {checked.member_id} already exists.")
            else:
                member.update(
                    member_id=checked.member_id,
                    name=checked.name,
                    email=checked.email,
                )
                the_library.save()
                flash(f"{member.name} updated.", "success")
                return redirect(url_for("views.members"))
    return render_template(
        "member_form.html",
        form=form,
        action=url_for("views.edit_member", member_id=member_id),
        title="Edit member",
        submit="Save changes",
    )


@blueprint.route("/members/<int:member_id>/delete", methods=["POST"])
@capability_required("delete_member")
def delete_member(member_id):
    result = library().remove_member(member_id)
    flash(result.message, "success" if result else "error")
    return redirect(url_for("views.members"))


# ----------------------------------------------------------------------- users
@blueprint.route("/users")
@admin_required
def users():
    return render_template("users.html", rows=library().staff_accounts())


@blueprint.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    form = {
        "username": "",
        "full_name": "",
        "role": "staff",
        "password": "",
        "password2": "",
    }
    if request.method == "POST":
        form = {
            "username": value("username").lower(),
            "full_name": value("full_name"),
            "role": value("role", "staff"),
            "password": request.form.get("password", ""),
            "password2": request.form.get("password2", ""),
        }
        problem = check_passwords(form["password"], form["password2"])
        if problem:
            fail(problem)
        else:
            try:
                user = User.create(
                    form["username"],
                    form["password"],
                    role=form["role"],
                    full_name=form["full_name"],
                )
            except (ValidationError, ValueError) as error:
                fail(str(error))
            else:
                result = library().add_user(user)
                flash(result.message, "success" if result else "error")
                if result:
                    return redirect(url_for("views.users"))
    return render_template(
        "user_form.html",
        form=form,
        action=url_for("views.new_user"),
        title="Add a staff account",
        submit="Create account",
    )


@blueprint.route("/users/<username>/role", methods=["POST"])
@admin_required
def change_role(username):
    the_library = library()
    user = the_library.find_user(username) or abort(404)
    new_role = value("role", "staff")
    if not User.role_is_valid(new_role):
        fail("That role does not exist.")
    elif user.username == g.user.username:
        fail("You cannot change your own role.")
    elif user.is_admin and new_role != User.ADMIN and len(the_library.admins()) <= 1:
        fail("The last administrator cannot be demoted.")
    else:
        user.role = new_role
        the_library.save()
        flash(f"{user.username} is now a {new_role}.", "success")
    return redirect(url_for("views.users"))


@blueprint.route("/users/<username>/delete", methods=["POST"])
@admin_required
def delete_user(username):
    the_library = library()
    if the_library.find_user(username) is None:
        abort(404)
    if username == g.user.username:
        fail("You cannot delete your own account.")
    else:
        result = the_library.remove_user(username)
        flash(result.message, "success" if result else "error")
    return redirect(url_for("views.users"))


# --------------------------------------------------------------------- profile
@blueprint.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        again = request.form.get("new_password2", "")
        the_library = library()
        problem = None
        if not the_library.authenticate(g.user.username, current):
            problem = "Your current password is not correct."
        else:
            problem = check_passwords(new, again)
        if problem:
            fail(problem)
        else:
            g.user.set_password(new)
            the_library.save()
            flash("Your password has been changed.", "success")
            return redirect(url_for("views.profile"))
    return render_template("profile.html", user=g.user)


# --------------------------------------------------------------------- helpers
def build_member(form):
    member_class = MEMBER_CLASSES.get(form.get("member_type"))
    if member_class is None:
        raise ValueError("Member type must be Student or Teacher.")
    return member_class(form["member_id"], form["name"], form["email"])


def check_passwords(password, again):
    if not password:
        return "Please enter a password."
    if len(password) < 8:
        return "The password must be at least 8 characters long."
    if password != again:
        return "The two passwords do not match."
    return None
