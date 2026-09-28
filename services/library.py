"""The Library class - composition.

A Library object *has* Book objects and Member objects.  It also coordinates
them: only the Library may decide that a book changes hands, so the book and
the member can never disagree with each other.
"""

from models import Book, User, ValidationError
from models.validators import clean_id, clean_text


class OperationResult:
    """What every Library action returns: did it work, and why not?

    The console version simply prints ``result.message``; the GUI shows it in
    a message box.  ``bool(result)`` is True on success.
    """

    def __init__(self, success, message):
        self.success = bool(success)
        self.message = message

    def __bool__(self):
        return self.success

    def __repr__(self):
        return f"OperationResult(success={self.success!r}, message={self.message!r})"


_dummy_cache = None


def _dummy_user():
    """A throwaway account, built once, used only to burn the same time."""
    global _dummy_cache
    if _dummy_cache is None:
        _dummy_cache = User("no-such-account", User.hash_password("unused-password"))
    return _dummy_cache


class Library:
    """The whole system: name, catalogue, members and the rules."""

    def __init__(self, name="My School Library", storage=None):
        self.name = clean_text(name, "Library name")
        self.books = []
        self.members = []
        self.users = []
        self.storage = storage
        self.last_save_error = None

    # -------------------------------------------------------------- catalogue
    def add_book(self, book):
        if not isinstance(book, Book):
            raise ValidationError("Only Book objects can be added.")
        if self.find_book(book.book_id) is not None:
            return OperationResult(False, f"A book with ID {book.book_id} already exists.")
        self.books.append(book)
        self.save()
        return OperationResult(True, f"'{book.title}' added successfully.")

    def remove_book(self, book_id):
        book = self.find_book(book_id)
        if book is None:
            return OperationResult(False, "Book not found.")
        if not book.is_available:
            return OperationResult(False, f"'{book.title}' is still borrowed. Return it first.")
        self.books.remove(book)
        self.save()
        return OperationResult(True, f"'{book.title}' removed successfully.")

    def register_member(self, member):
        if self.find_member(member.member_id) is not None:
            return OperationResult(False, f"A member with ID {member.member_id} already exists.")
        self.members.append(member)
        self.save()
        return OperationResult(True, f"{member.name} registered successfully.")

    def remove_member(self, member_id):
        member = self.find_member(member_id)
        if member is None:
            return OperationResult(False, "Member not found.")
        if member.borrowed_count():
            return OperationResult(False, f"{member.name} still has borrowed books.")
        self.members.remove(member)
        self.save()
        return OperationResult(True, f"{member.name} removed successfully.")

    # ---------------------------------------------------------------- lookups
    def find_book(self, book_id):
        try:
            wanted = clean_id(book_id, "Book ID")
        except ValidationError:
            return None
        for book in self.books:
            if book.book_id == wanted:
                return book
        return None

    def find_member(self, member_id):
        try:
            wanted = clean_id(member_id, "Member ID")
        except ValidationError:
            return None
        for member in self.members:
            if member.member_id == wanted:
                return member
        return None

    def get_available_books(self):
        return [book for book in self.books if book.is_available]

    def get_borrowed_books(self):
        return [book for book in self.books if not book.is_available]

    def find_books(self, keyword):
        """Books whose title, author or category match the keyword."""
        return [book for book in self.books if book.matches(keyword)]

    def find_member_by_name(self, name):
        wanted = str(name).strip().lower()
        for member in self.members:
            if wanted in member.name.lower():
                return member
        return None

    def next_book_id(self):
        return max((book.book_id for book in self.books), default=100) + 1

    def next_member_id(self):
        return max((member.member_id for member in self.members), default=0) + 1

    # ---------------------------------------------------------- transactions
    def borrow_book(self, member_id, book_id):
        member = self.find_member(member_id)
        if member is None:
            return OperationResult(False, "Member not found.")

        book = self.find_book(book_id)
        if book is None:
            return OperationResult(False, "Book not found.")

        if not book.is_available:
            return OperationResult(False, "Book is already borrowed.")

        if member.has_borrowed(book):
            return OperationResult(False, f"{member.name} already borrowed this book.")

        if member.has_reached_limit():
            return OperationResult(
                False,
                f"Borrowing limit reached ({member.borrowing_limit()} books for a {member.member_type().lower()}).",
            )

        member.borrow_book(book)
        book.mark_borrowed()
        self.save()
        return OperationResult(True, f"{member.name} borrowed '{book.title}' successfully.")

    def return_book(self, member_id, book_id):
        member = self.find_member(member_id)
        if member is None:
            return OperationResult(False, "Member not found.")

        book = self.find_book(book_id)
        if book is None:
            return OperationResult(False, "Book not found.")

        if not member.has_borrowed(book):
            return OperationResult(False, "This member did not borrow this book.")

        member.return_book(book)
        book.mark_returned()
        self.save()
        return OperationResult(True, f"{member.name} returned '{book.title}' successfully.")

    # ------------------------------------------------------------------ users
    def find_user(self, username):
        wanted = str(username or "").strip().lower()
        for user in self.users:
            if user.username == wanted:
                return user
        return None

    def authenticate(self, username, password):
        """Return the User when the password is right, otherwise None."""
        user = self.find_user(username)
        if user is None:
            # Hash something anyway, so that an unknown username takes the same
            # time as a known one with a wrong password.
            _dummy_user().check_password(password)
            return None
        if not user.check_password(password):
            return None
        return user

    def add_user(self, user):
        if not isinstance(user, User):
            raise ValidationError("Only User objects can be added.")
        if self.find_user(user.username) is not None:
            return OperationResult(False, f"The username '{user.username}' is already taken.")
        self.users.append(user)
        self.save()
        return OperationResult(True, f"Account '{user.username}' created.")

    def remove_user(self, username):
        user = self.find_user(username)
        if user is None:
            return OperationResult(False, "Account not found.")
        if len(self.admins()) <= 1 and user.is_admin:
            return OperationResult(False, "The last administrator cannot be deleted.")
        self.users.remove(user)
        self.save()
        return OperationResult(True, f"Account '{user.username}' deleted.")

    def admins(self):
        return [user for user in self.users if user.is_admin]

    def staff_accounts(self):
        return sorted(self.users, key=lambda user: (not user.is_admin, user.username))

    # ------------------------------------------------------------- reporting
    def display_books(self):
        if not self.books:
            print("\n===== BOOK LIST =====")
            print("No books in the library yet.")
            return
        print("\n===== BOOK LIST =====")
        for book in self.books:
            book.display_info()
            print("---------------------")

    def display_members(self):
        if not self.members:
            print("\n===== MEMBER LIST =====")
            print("No members registered yet.")
            return
        print("\n===== MEMBER LIST =====")
        for member in self.members:
            member.display_info()
            member.display_borrowed_books()
            print("-----------------------")

    def search_book(self, keyword):
        """Console version of :meth:`find_books`."""
        matches = self.find_books(keyword)
        if not matches:
            print("No book found.")
            return
        for book in matches:
            book.display_info()
            print("------------------")

    def statistics(self):
        borrowed_by_type = {}
        for member in self.members:
            key = member.member_type()
            borrowed_by_type[key] = borrowed_by_type.get(key, 0) + member.borrowed_count()
        return {
            "total_books": len(self.books),
            "available_books": len(self.get_available_books()),
            "borrowed_books": len(self.get_borrowed_books()),
            "total_members": len(self.members),
            "borrowed_by_type": borrowed_by_type,
        }

    def display_statistics(self):
        stats = self.statistics()
        print("\n===== STATISTICS =====")
        print(f"Total books      : {stats['total_books']}")
        print(f"Available books  : {stats['available_books']}")
        print(f"Borrowed books   : {stats['borrowed_books']}")
        print(f"Total members    : {stats['total_members']}")
        for member_type, count in sorted(stats["borrowed_by_type"].items()):
            print(f"  {member_type:<12}: {count} borrowed")

    # ------------------------------------------------------------ persistence
    def load(self):
        """Fill this library from the storage layer, if one was given."""
        if self.storage is None:
            return self
        self.storage.load_into(self)
        return self

    def save(self):
        """Write to disk, if storage is configured. Never raises."""
        if self.storage is None:
            return True
        try:
            self.storage.save_from(self)
        except OSError as error:
            self.last_save_error = str(error)
            print(f"Warning: could not save the data file ({error}).")
            return False
        self.last_save_error = None
        return True
