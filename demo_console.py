"""A self-contained version of the whole system in a single file.

Run it with:  python demo_console.py   (add --demo for a scripted tour)

Everything lives in one file so the classes can be read side by side:
``Book``, ``Member`` (with the ``StudentMember`` and ``TeacherMember``
subclasses) and ``Library``.  There is no file storage here, so every change
is lost when the program ends.  ``main.py`` is the same system split into
packages, with JSON storage and a GUI.
"""

import sys


# =============================================================================
# 1. Book - class, __init__, instance attributes, methods
# =============================================================================
class Book:
    def __init__(self, book_id, title, author, category):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.category = category
        self.is_available = True

    def display_info(self):
        status = "Available" if self.is_available else "Borrowed"

        print(f"ID: {self.book_id}")
        print(f"Title: {self.title}")
        print(f"Author: {self.author}")
        print(f"Category: {self.category}")
        print(f"Status: {status}")

    def display_short(self):
        status = "Available" if self.is_available else "Borrowed"
        print(f"[{self.book_id:>3}] {self.title:<30} {self.author:<20} {status}")


# =============================================================================
# 2. Member - lists of objects, methods
# =============================================================================
class Member:
    def __init__(self, member_id, name, email):
        self.member_id = member_id
        self.name = name
        self.email = email
        self.borrowed_books = []

    def borrow_book(self, book):
        self.borrowed_books.append(book)

    def return_book(self, book):
        self.borrowed_books.remove(book)

    def borrowed_count(self):
        return len(self.borrowed_books)

    def has_borrowed(self, book):
        return book in self.borrowed_books

    def display_info(self):
        print(f"ID: {self.member_id}")
        print(f"Name: {self.name}")
        print(f"Email: {self.email}")
        print(f"Borrowed Books: {len(self.borrowed_books)}")

    def display_borrowed_books(self):
        if not self.borrowed_books:
            print("  (no borrowed books)")
            return
        for book in self.borrowed_books:
            print(f"  - [{book.book_id}] {book.title}")

    def borrowing_limit(self):
        return 3

    def member_type(self):
        return "Member"


# =============================================================================
# 3. Inheritance - StudentMember and TeacherMember are Members
# =============================================================================
class StudentMember(Member):
    def borrowing_limit(self):
        return 3

    def member_type(self):
        return "Student"


class TeacherMember(Member):
    def borrowing_limit(self):
        return 10

    def member_type(self):
        return "Teacher"


# =============================================================================
# 4. Encapsulation - the list is private, the class protects it
# =============================================================================
class SafeMember(Member):
    """Same as Member, but the list of books cannot be touched from outside.

    ``self.__borrowed_books`` is hidden by Python: writing to
    ``member.borrowed_books`` creates a *new*, empty attribute and breaks the
    member, so every change has to go through the methods below.
    """

    def __init__(self, member_id, name, email):
        super().__init__(member_id, name, email)
        self.__borrowed_books = []

    def get_borrowed_books(self):
        return self.__borrowed_books

    def add_book(self, book):
        if book in self.__borrowed_books:
            return False
        if len(self.__borrowed_books) >= self.borrowing_limit():
            return False
        self.__borrowed_books.append(book)
        return True

    def remove_book(self, book):
        if book in self.__borrowed_books:
            self.__borrowed_books.remove(book)
            return True
        return False

    def borrow_book(self, book):
        return self.add_book(book)

    def return_book(self, book):
        return self.remove_book(book)

    def has_reached_limit(self):
        return len(self.__borrowed_books) >= self.borrowing_limit()

    def borrowed_count(self):
        return len(self.__borrowed_books)

    def has_borrowed(self, book):
        return book in self.__borrowed_books

    def member_type(self):
        return "Member"

    def display_info(self):
        print(f"ID: {self.member_id}")
        print(f"Name: {self.name}")
        print(f"Email: {self.email}")
        print(f"Limit: {self.borrowing_limit()} books")
        print(f"Borrowed Books: {len(self.__borrowed_books)}")

    def display_borrowed_books(self):
        if not self.__borrowed_books:
            print("  (no borrowed books)")
            return
        for book in self.__borrowed_books:
            print(f"  - [{book.book_id}] {book.title}")


class SafeStudentMember(SafeMember):
    def borrowing_limit(self):
        return 3

    def member_type(self):
        return "Student"


class SafeTeacherMember(SafeMember):
    def borrowing_limit(self):
        return 10

    def member_type(self):
        return "Teacher"


# =============================================================================
# 5. Library - composition: the Library *has* books and members
# =============================================================================
class Library:
    def __init__(self, name):
        self.name = name
        self.books = []
        self.members = []

    def add_book(self, book):
        self.books.append(book)
        print("Book added successfully.")

    def register_member(self, member):
        self.members.append(member)
        print("Member registered successfully.")

    def find_book(self, book_id):
        for book in self.books:
            if book.book_id == book_id:
                return book
        return None

    def find_member(self, member_id):
        for member in self.members:
            if member.member_id == member_id:
                return member
        return None

    def display_books(self):
        print("\n===== BOOK LIST =====")
        for book in self.books:
            book.display_info()
            print("---------------------")

    def display_books_short(self):
        print("\n===== BOOK LIST =====")
        print(f"{'ID':>4} {'TITLE':<30} {'AUTHOR':<20} STATUS")
        for book in self.books:
            book.display_short()
        print("---------------------")

    def display_members(self):
        print("\n===== MEMBER LIST =====")
        for member in self.members:
            member.display_info()
            print("-----------------------")

    def display_members_short(self):
        print("\n===== MEMBER LIST =====")
        print(f"{'ID':>4} {'NAME':<20} {'TYPE':<10} {'LIMIT':>5} {'BORROWED':>8}")
        for member in self.members:
            print(
                f"{member.member_id:>4} {member.name:<20} {member.member_type():<10} "
                f"{member.borrowing_limit():>5} {member.borrowed_count():>8}"
            )
        print("-----------------------")

    def borrow_book(self, member_id, book_id):
        member = None
        book = None

        for m in self.members:
            if m.member_id == member_id:
                member = m

        for b in self.books:
            if b.book_id == book_id:
                book = b

        if member is None:
            print("Member not found.")
            return

        if book is None:
            print("Book not found.")
            return

        if not book.is_available:
            print("Book is already borrowed.")
            return

        if member.borrowed_count() >= member.borrowing_limit():
            print("Borrowing limit reached.")
            return

        member.borrow_book(book)
        book.is_available = False

        print(f"{member.name} borrowed '{book.title}' successfully.")

    def return_book(self, member_id, book_id):
        member = None
        book = None

        for m in self.members:
            if m.member_id == member_id:
                member = m

        for b in self.books:
            if b.book_id == book_id:
                book = b

        if member is None:
            print("Member not found.")
            return

        if book is None:
            print("Book not found.")
            return

        if not member.has_borrowed(book):
            print("This member did not borrow this book.")
            return

        member.return_book(book)
        book.is_available = True

        print(f"{member.name} returned '{book.title}' successfully.")

    def search_book(self, keyword):
        found = False
        for book in self.books:
            if (
                keyword.lower() in book.title.lower()
                or keyword.lower() in book.author.lower()
            ):
                book.display_info()
                print("------------------")
                found = True

        if not found:
            print("No book found.")


# =============================================================================
# 6. The running program
# =============================================================================
def build_demo_library():
    """Create the sample books and members and register them."""
    library = Library("My School Library")

    library.add_book(Book(101, "Python Programming", "John Smith", "Programming"))
    library.add_book(Book(102, "Data Structures", "Robert Brown", "Computer Science"))
    library.add_book(Book(103, "Clean Code", "Robert Martin", "Programming"))
    library.add_book(Book(104, "Database Systems", "Silberschatz", "Computer Science"))

    library.register_member(SafeStudentMember(1, "Mg Mg", "mgmg@gmail.com"))
    library.register_member(SafeTeacherMember(2, "U Aung", "uaung@gmail.com"))
    library.register_member(SafeStudentMember(3, "Ma Ma", "mama@gmail.com"))

    return library


def show_polymorphism(library):
    """4. Polymorphism: one call, a different answer for each object."""
    print("\n===== POLYMORPHISM =====")
    for member in library.members:
        print(f"{member.name} can borrow {member.borrowing_limit()} books")
    print()
    print("Same method: member.borrowing_limit()")
    print("Different result, because the object is a different subclass.")


def show_encapsulation(member):
    """6. Encapsulation: the real list cannot be reached from outside."""
    print("\n===== ENCAPSULATION =====")
    extra_books = [
        Book(201, "The Pragmatic Programmer", "Andrew Hunt", "Programming"),
        Book(202, "Refactoring", "Martin Fowler", "Programming"),
        Book(203, "Design Patterns", "Erich Gamma", "Programming"),
    ]
    for book in extra_books:
        added = member.add_book(book)
        print(f"  {'Added  ' if added else 'Refused'} [{book.book_id}] {book.title}")

    print(f"\n{member.name} may borrow {member.borrowing_limit()} books and now holds "
          f"{member.borrowed_count()}.")
    one_more = Book(204, "Code Complete", "Steve McConnell", "Programming")
    print(f"  {'Added  ' if member.add_book(one_more) else 'Refused'} [{one_more.book_id}] "
          f"{one_more.title}  <- the limit protects the list")

    member.return_book(extra_books[0])
    print(f"After returning one book: {member.borrowed_count()}")


def read_int(prompt):
    while True:
        value = input(prompt).strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            print("Please type a whole number.")


MENU = (
    ("1", "List books", "display_books_short"),
    ("2", "List members", "display_members_short"),
    ("3", "Borrow book", "borrow"),
    ("4", "Return book", "return"),
    ("5", "Search book", "search"),
)


def run_console(library):
    print("\n(This version has no file storage: changes are lost when it ends.)")
    while True:
        print("\n===== LIBRARY MANAGEMENT SYSTEM =====")
        for key, label, _ in MENU:
            print(f"  {key}. {label}")
        print("  P. Show polymorphism")
        print("  E. Show encapsulation")
        print("  0. Exit")

        choice = input("Choose an option: ").strip().upper()

        if choice == "0":
            print("Goodbye!")
            break
        if choice == "P":
            show_polymorphism(library)
            continue
        if choice == "E":
            show_encapsulation(library.find_member(1))
            continue

        action = next((a for k, _, a in MENU if k == choice), None)
        if action is None:
            print("Unknown option.")
            continue
        if action == "borrow":
            member_id = read_int("Member ID: ")
            book_id = read_int("Book ID: ")
            if member_id is not None and book_id is not None:
                library.borrow_book(member_id, book_id)
        elif action == "return":
            member_id = read_int("Member ID: ")
            book_id = read_int("Book ID: ")
            if member_id is not None and book_id is not None:
                library.return_book(member_id, book_id)
        elif action == "search":
            keyword = input("Title or author: ").strip()
            if keyword:
                library.search_book(keyword)
        else:
            getattr(library, action)()


def run_tour(library):
    """The non-interactive part: a tour of every feature."""
    library.display_books_short()
    library.display_members_short()
    show_polymorphism(library)
    show_encapsulation(library.find_member(1))

    print("\n===== BORROW AND RETURN =====")
    library.borrow_book(1, 101)
    library.borrow_book(2, 102)
    library.borrow_book(1, 101)  # already borrowed
    library.borrow_book(1, 103)
    library.borrow_book(1, 104)  # over the student limit
    library.return_book(1, 103)
    library.return_book(1, 102)  # never borrowed it

    print("\n===== SEARCH =====")
    library.search_book("Robert")

    print("\n===== BOOK LIST AFTER THE LOANS =====")
    library.display_books_short()


def main():
    library = build_demo_library()

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_tour(library)
        return

    try:
        run_console(library)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
