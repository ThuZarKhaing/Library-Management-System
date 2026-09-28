"""The Book class - a single item in the library catalogue."""

from .validators import clean_id, clean_text


class Book:
    """One book in the library catalogue.

    The public data (id, title, author, category) stays readable, while
    ``is_available`` is guarded by a property so nobody can set it to
    something strange.
    """

    def __init__(self, book_id, title, author, category="General", is_available=True):
        self.book_id = clean_id(book_id, "Book ID")
        self.title = clean_text(title, "Title")
        self.author = clean_text(author, "Author")
        self.category = clean_text(category, "Category")
        self._is_available = bool(is_available)

    # ------------------------------------------------------------ properties
    @property
    def is_available(self):
        return self._is_available

    @is_available.setter
    def is_available(self, value):
        self._is_available = bool(value)

    @property
    def status(self):
        return "Available" if self._is_available else "Borrowed"

    # ---------------------------------------------------------------- methods
    def mark_borrowed(self):
        self._is_available = False

    def mark_returned(self):
        self._is_available = True

    def matches(self, keyword):
        """True when the keyword appears in the title, author or category."""
        needle = str(keyword).strip().lower()
        if not needle:
            return True
        return (
            needle in self.title.lower()
            or needle in self.author.lower()
            or needle in self.category.lower()
        )

    def update(self, book_id=None, title=None, author=None, category=None):
        """Change the details in place.

        The same object is kept, so a member who has this book on loan still
        points at the book that was edited.
        """
        if book_id is not None:
            self.book_id = clean_id(book_id, "Book ID")
        if title is not None:
            self.title = clean_text(title, "Title")
        if author is not None:
            self.author = clean_text(author, "Author")
        if category is not None:
            self.category = clean_text(category, "Category")
        return self

    def display_info(self):
        print(f"ID: {self.book_id}")
        print(f"Title: {self.title}")
        print(f"Author: {self.author}")
        print(f"Category: {self.category}")
        print(f"Status: {self.status}")

    # ------------------------------------------------------ saving and loading
    def to_dict(self):
        return {
            "book_id": self.book_id,
            "title": self.title,
            "author": self.author,
            "category": self.category,
            "is_available": self.is_available,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            book_id=data["book_id"],
            title=data["title"],
            author=data["author"],
            category=data.get("category", "General"),
            is_available=data.get("is_available", True),
        )

    # ---------------------------------------------------------- dunder methods
    def __str__(self):
        return f"[{self.book_id}] {self.title} by {self.author}"

    def __repr__(self):
        return (
            f"Book(book_id={self.book_id!r}, title={self.title!r}, "
            f"author={self.author!r}, category={self.category!r})"
        )

    def __eq__(self, other):
        if not isinstance(other, Book):
            return NotImplemented
        return self.book_id == other.book_id

    def __hash__(self):
        return hash((Book, self.book_id))
