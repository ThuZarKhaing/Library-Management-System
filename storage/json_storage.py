"""JSON storage: the catalogue and the members are kept in two files.

Flow of the program:

    start -> load books.json -> load members.json -> build objects
          -> user works -> every change is saved -> close

Books are saved as a list of dictionaries.  Members are saved with the *ids*
of the books they hold, because a Book object is already described by
``books.json``; that keeps the two files from contradicting each other.
"""

import json
from pathlib import Path

from models import Book, User, member_from_dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

SAMPLE_BOOKS = [
    (101, "Python Programming", "John Smith", "Programming"),
    (102, "Data Structures", "Robert Brown", "Computer Science"),
    (103, "Clean Code", "Robert Martin", "Programming"),
    (104, "Introduction to Algorithms", "Thomas Cormen", "Computer Science"),
    (105, "The Great Gatsby", "F. Scott Fitzgerald", "Fiction"),
    (106, "Database Systems", "Silberschatz", "Computer Science"),
]

SAMPLE_MEMBERS = [
    (1, "Mg Mg", "mgmg@gmail.com", "Student"),
    (2, "U Aung", "uaung@gmail.com", "Teacher"),
    (3, "Ma Ma", "mama@gmail.com", "Student"),
]

# Only used when users.json is missing. Change these before putting the system
# on a real network.
DEFAULT_USERS = [
    ("admin", "admin12345", "admin", "Library Administrator"),
    ("staff", "staff12345", "staff", "Front Desk Staff"),
]


class LibraryStorage:
    """Reads and writes ``books.json`` and ``members.json``."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.books_file = self.data_dir / "books.json"
        self.members_file = self.data_dir / "members.json"
        self.users_file = self.data_dir / "users.json"

    # ---------------------------------------------------------------- helpers
    def ensure_data_dir(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _read_json(self, path, default):
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            # A damaged file must not stop the program from starting.
            return default
        return data if isinstance(data, type(default)) else default

    def _write_json(self, path, data):
        self.ensure_data_dir()
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4, ensure_ascii=False)
            handle.write("\n")

    # ------------------------------------------------------------------ books
    def load_books(self):
        records = self._read_json(self.books_file, [])
        books = []
        for record in records:
            try:
                books.append(Book.from_dict(record))
            except (KeyError, TypeError, ValueError):
                continue  # skip a broken record instead of losing the file
        return books

    def save_books(self, books):
        self._write_json(self.books_file, [book.to_dict() for book in books])

    # ---------------------------------------------------------------- members
    def load_members(self, book_lookup=None):
        records = self._read_json(self.members_file, [])
        members = []
        for record in records:
            try:
                members.append(member_from_dict(record, book_lookup=book_lookup))
            except (KeyError, TypeError, ValueError):
                continue
        return members

    def save_members(self, members):
        self._write_json(self.members_file, [member.to_dict() for member in members])

    # ------------------------------------------------------------------ users
    def load_users(self):
        records = self._read_json(self.users_file, [])
        users = []
        for record in records:
            try:
                users.append(User.from_dict(record))
            except (KeyError, TypeError, ValueError):
                continue
        return users

    def save_users(self, users):
        self._write_json(self.users_file, [user.to_dict() for user in users])

    # ------------------------------------------------------------ whole system
    def load_into(self, library):
        """Replace the contents of ``library`` with what is on disk."""
        books = self.load_books()
        book_lookup = {book.book_id: book for book in books}
        library.books = books
        library.members = self.load_members(book_lookup=book_lookup)
        library.users = self.load_users()
        if not books and not library.members:
            self.seed(library)
        if not library.users:
            self.seed_users(library)
        return library

    def save_from(self, library):
        self.save_books(library.books)
        self.save_members(library.members)
        self.save_users(library.users)

    # ------------------------------------------------------------------ seeds
    def seed(self, library):
        """Put a few example books and members in the files on first run."""
        from models import StudentMember, TeacherMember

        classes = {"Student": StudentMember, "Teacher": TeacherMember}
        for book_id, title, author, category in SAMPLE_BOOKS:
            library.books.append(Book(book_id, title, author, category))
        for member_id, name, email, member_type in SAMPLE_MEMBERS:
            member_class = classes[member_type]
            library.members.append(member_class(member_id, name, email))
        self.save_from(library)

    def seed_users(self, library):
        """Create the first admin and staff accounts when none exist."""
        for username, password, role, full_name in DEFAULT_USERS:
            library.users.append(
                User.create(username, password, role=role, full_name=full_name)
            )
        self.save_users(library.users)
