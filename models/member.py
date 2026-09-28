"""The Member base class - lists of objects plus encapsulation."""

from .book import Book
from .validators import ValidationError, clean_email, clean_id, clean_text


class Member:
    """Base class for everybody who can borrow books.

    The list of borrowed books is stored in ``self.__borrowed_books``.  The two
    leading underscores make Python hide it (``_Member__borrowed_books``), so
    the only way to change it is through the methods below.  That is
    encapsulation: the class protects its own data.
    """

    MEMBER_TYPE = "Member"
    BORROWING_LIMIT = 3
    LOAN_DAYS = 14

    def __init__(self, member_id, name, email, borrowed_books=None):
        self.member_id = clean_id(member_id, "Member ID")
        self.name = clean_text(name, "Name")
        self.email = clean_email(email)
        self.__borrowed_books = []
        for book in borrowed_books or []:
            self.add_borrowed_book(book)

    # ------------------------------------------- methods subclasses may change
    def borrowing_limit(self):
        """How many books this member may hold at the same time."""
        return self.BORROWING_LIMIT

    def member_type(self):
        return self.MEMBER_TYPE

    def loan_days(self):
        return self.LOAN_DAYS

    # --------------------------------------------------------- encapsulation
    def get_borrowed_books(self):
        """Return a copy of the list, so callers cannot edit the real one."""
        return list(self.__borrowed_books)

    def borrowed_count(self):
        return len(self.__borrowed_books)

    def has_borrowed(self, book):
        return book in self.__borrowed_books

    def has_reached_limit(self):
        return self.borrowed_count() >= self.borrowing_limit()

    def add_borrowed_book(self, book):
        """Add a book. Returns False if it is already held or the limit is full."""
        if not isinstance(book, Book):
            raise ValidationError("Only Book objects can be borrowed.")
        if self.has_borrowed(book):
            return False
        if self.has_reached_limit():
            return False
        self.__borrowed_books.append(book)
        return True

    def remove_borrowed_book(self, book):
        """Remove a book. Returns False when the member never had it."""
        if book in self.__borrowed_books:
            self.__borrowed_books.remove(book)
            return True
        return False

    # Shorter names for the same two actions.
    def borrow_book(self, book):
        return self.add_borrowed_book(book)

    def return_book(self, book):
        return self.remove_borrowed_book(book)

    # ---------------------------------------------------------------- display
    def update(self, member_id=None, name=None, email=None):
        """Change the details in place, keeping the same borrowed books."""
        if member_id is not None:
            self.member_id = clean_id(member_id, "Member ID")
        if name is not None:
            self.name = clean_text(name, "Name")
        if email is not None:
            self.email = clean_email(email)
        return self

    def display_info(self):
        print(f"ID: {self.member_id}")
        print(f"Name: {self.name}")
        print(f"Email: {self.email}")
        print(f"Type: {self.member_type()}")
        print(f"Limit: {self.borrowing_limit()} books")
        print(f"Borrowed Books: {self.borrowed_count()}")

    def display_borrowed_books(self):
        if not self.__borrowed_books:
            print("  (no borrowed books)")
            return
        for book in self.__borrowed_books:
            print(f"  - [{book.book_id}] {book.title}")

    # ------------------------------------------------------ saving and loading
    def to_dict(self):
        return {
            "member_id": self.member_id,
            "name": self.name,
            "email": self.email,
            "member_type": self.member_type(),
            "borrowed_book_ids": [book.book_id for book in self.__borrowed_books],
        }

    @classmethod
    def from_dict(cls, data, book_lookup=None):
        """Rebuild a member. ``book_lookup`` maps book_id -> Book object."""
        lookup = book_lookup or {}
        borrowed = []
        for book_id in data.get("borrowed_book_ids", []):
            book = lookup.get(int(book_id))
            if book is not None:
                borrowed.append(book)
        return cls(
            member_id=data["member_id"],
            name=data["name"],
            email=data["email"],
            borrowed_books=borrowed,
        )

    # ---------------------------------------------------------- dunder methods
    def __str__(self):
        return f"[{self.member_id}] {self.name} ({self.member_type()})"

    def __repr__(self):
        return (
            f"{type(self).__name__}(member_id={self.member_id!r}, "
            f"name={self.name!r}, email={self.email!r})"
        )
