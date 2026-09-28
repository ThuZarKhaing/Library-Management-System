"""Library Management System - entry point.

    python main.py          console menu
    python main.py --gui    desktop application
    python main.py --web    web dashboard with staff and admin logins
    python main.py --demo   short non-interactive tour of every feature
"""

import sys

from models import Book, StudentMember, TeacherMember, ValidationError
from services import Library
from storage import LibraryStorage

MEMBER_CLASSES = {"1": StudentMember, "2": TeacherMember}


def read_int(prompt):
    """Ask for a number until a valid one is given."""
    while True:
        value = input(prompt).strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            print("Please type a whole number.")


def read_text(prompt, default=""):
    value = input(prompt).strip()
    return value or default


def ask_yes_no(prompt):
    return input(prompt).strip().lower() in ("y", "yes")


def build_library():
    """Create the library and load the JSON files into it."""
    storage = LibraryStorage()
    library = Library("My School Library", storage=storage)
    library.load()
    return library


# ---------------------------------------------------------------- menu actions
def action_add_book(library):
    print("\n--- Add Book ---")
    try:
        book_id = read_int("Book ID (leave empty to auto assign): ")
        if book_id is None:
            book_id = library.next_book_id()
        title = read_text("Title: ")
        author = read_text("Author: ")
        category = read_text("Category: ", "General")
    except ValidationError as error:
        print(f"Error: {error}")
        return

    result = library.add_book(Book(book_id, title, author, category))
    print(result.message)


def action_add_member(library):
    print("\n--- Add Member ---")
    print("1. Student (3 books)   2. Teacher (10 books)")
    choice = read_text("Member type [1]: ", "1")
    if choice not in MEMBER_CLASSES:
        print("Error: member type must be 1 (student) or 2 (teacher).")
        return
    member_class = MEMBER_CLASSES[choice]

    try:
        member_id = read_int("Member ID (leave empty to auto assign): ")
        if member_id is None:
            member_id = library.next_member_id()
        name = read_text("Name: ")
        email = read_text("Email: ")
    except ValidationError as error:
        print(f"Error: {error}")
        return

    result = library.register_member(member_class(member_id, name, email))
    print(result.message)


def action_borrow_book(library):
    print("\n--- Borrow Book ---")
    member_id = read_int("Member ID: ")
    if member_id is None:
        return
    book_id = read_int("Book ID: ")
    if book_id is None:
        return
    print(library.borrow_book(member_id, book_id).message)


def action_return_book(library):
    print("\n--- Return Book ---")
    member_id = read_int("Member ID: ")
    if member_id is None:
        return
    book_id = read_int("Book ID: ")
    if book_id is None:
        return
    print(library.return_book(member_id, book_id).message)


def action_search_book(library):
    print("\n--- Search Book ---")
    keyword = read_text("Title or author: ")
    if not keyword:
        return
    library.search_book(keyword)


def action_view_member(library):
    print("\n--- Member Details ---")
    member_id = read_int("Member ID: ")
    if member_id is None:
        return
    member = library.find_member(member_id)
    if member is None:
        print("Member not found.")
        return
    member.display_info()
    member.display_borrowed_books()


def action_remove_book(library):
    print("\n--- Remove Book ---")
    book_id = read_int("Book ID: ")
    if book_id is None:
        return
    if not ask_yes_no("Really remove this book? (y/n): "):
        print("Cancelled.")
        return
    print(library.remove_book(book_id).message)


MENU = (
    ("1", "Add Book", action_add_book),
    ("2", "List Books", lambda library: library.display_books()),
    ("3", "Search Book", action_search_book),
    ("4", "Add Member", action_add_member),
    ("5", "List Members", lambda library: library.display_members()),
    ("6", "Member Details", action_view_member),
    ("7", "Borrow Book", action_borrow_book),
    ("8", "Return Book", action_return_book),
    ("9", "Remove Book", action_remove_book),
    ("S", "Statistics", lambda library: library.display_statistics()),
    ("0", "Exit", None),
)


def print_menu():
    print("\n===== LIBRARY MANAGEMENT SYSTEM =====")
    for key, label, _ in MENU:
        print(f"  {key:>2}. {label}")


def run_console(library):
    while True:
        print_menu()
        choice = input("Choose an option: ").strip().upper()
        if choice == "0":
            library.save()
            print("Data saved. Goodbye!")
            break
        for key, _, action in MENU:
            if key == choice and action is not None:
                action(library)
                break
        else:
            print("Unknown option. Please choose a number from the menu.")


# ------------------------------------------------------------------- demo mode
def run_demo(library):
    """A scripted tour - handy for marking and for showing students the output."""
    library.display_books()

    print("\n--- Polymorphism: same method, different answer ---")
    for member in library.members:
        print(f"{member.name} ({member.member_type()}) can borrow {member.borrowing_limit()} books")

    print("\n--- Borrow / return ---")
    print(library.borrow_book(1, 101).message)
    print(library.borrow_book(1, 102).message)
    print(library.borrow_book(1, 103).message)
    print(library.borrow_book(1, 104).message)  # over the student limit of 3
    print(library.borrow_book(1, 101).message)  # already borrowed
    print(library.return_book(1, 101).message)

    print("\n--- Member details ---")
    library.find_member(1).display_info()
    library.find_member(1).display_borrowed_books()

    print("\n--- Search ---")
    library.search_book("Robert")

    print("\n--- Statistics ---")
    library.display_statistics()


# -------------------------------------------------------------------- web mode
def run_web(library, host="127.0.0.1", port=5000, debug=False):
    """Start the web dashboard. Needs Flask: pip install -r requirements.txt"""
    try:
        from web import create_app
    except ImportError:
        print("Flask is not installed. Run:  pip install -r requirements.txt")
        return 1

    app = create_app(library)
    print(f"Web dashboard:  http://{host}:{port}")
    print("Sign in with admin / admin12345  or  staff / staff12345")
    print("Change these passwords from the account page after the first sign in.")
    print("Press Ctrl+C to stop.")
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        print("\nServer stopped. Goodbye!")
    return 0


# ------------------------------------------------------------------------ main
def main():
    args = sys.argv[1:]
    library = build_library()

    if "--gui" in args:
        from gui.app import launch_gui

        launch_gui(library)
        return

    if "--web" in args:
        raise SystemExit(
            run_web(
                library,
                host="0.0.0.0" if "--host" in args else "127.0.0.1",
                port=5000,
            )
        )

    if "--demo" in args:
        run_demo(library)
        return

    print(f"Welcome to the {library.name}!")
    print(f"Loaded {len(library.books)} books and {len(library.members)} members.")
    try:
        run_console(library)
    except (KeyboardInterrupt, EOFError):
        library.save()
        print("\nData saved. Goodbye!")


if __name__ == "__main__":
    main()
