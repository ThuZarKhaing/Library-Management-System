"""Tests for the whole project:  python -m unittest discover -s tests -v"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from models import Book, Member, StudentMember, TeacherMember, ValidationError
from services import Library
from storage import LibraryStorage


def make_library():
    library = Library("Test Library")
    library.add_book(Book(101, "Python Programming", "John Smith", "Programming"))
    library.add_book(Book(102, "Data Structures", "Robert Brown", "Computer Science"))
    library.add_book(Book(103, "Clean Code", "Robert Martin", "Programming"))
    library.register_member(StudentMember(1, "Mg Mg", "mgmg@gmail.com"))
    library.register_member(TeacherMember(2, "U Aung", "uaung@gmail.com"))
    return library


class TestBook(unittest.TestCase):
    def test_attributes_and_status(self):
        book = Book(101, "Python Programming", "John Smith", "Programming")
        self.assertEqual(book.book_id, 101)
        self.assertEqual(book.status, "Available")
        book.mark_borrowed()
        self.assertEqual(book.status, "Borrowed")
        book.mark_returned()
        self.assertEqual(book.status, "Available")

    def test_is_available_accepts_truthy_values(self):
        book = Book(1, "A", "B", "C")
        book.is_available = 0
        self.assertFalse(book.is_available)

    def test_validation(self):
        with self.assertRaises(ValidationError):
            Book("abc", "Title", "Author", "Cat")
        with self.assertRaises(ValidationError):
            Book(1, "   ", "Author", "Cat")

    def test_matches(self):
        book = Book(1, "Python Programming", "John Smith", "Programming")
        self.assertTrue(book.matches("python"))
        self.assertTrue(book.matches("SMITH"))
        self.assertTrue(book.matches(""))
        self.assertFalse(book.matches("novel"))

    def test_equality_by_id(self):
        self.assertEqual(Book(1, "A", "B", "C"), Book(1, "Different", "Other", "X"))
        self.assertNotEqual(Book(1, "A", "B", "C"), Book(2, "A", "B", "C"))


class TestMemberAndInheritance(unittest.TestCase):
    def test_student_and_teacher_limits(self):
        student = StudentMember(1, "Mg Mg", "mgmg@gmail.com")
        teacher = TeacherMember(2, "U Aung", "uaung@gmail.com")
        self.assertEqual(student.borrowing_limit(), 3)
        self.assertEqual(teacher.borrowing_limit(), 10)
        self.assertIsInstance(student, Member)

    def test_polymorphism(self):
        members = [StudentMember(1, "Mg Mg", "a@b.com"), TeacherMember(2, "U Aung", "c@d.com")]
        limits = [member.borrowing_limit() for member in members]
        self.assertEqual(limits, [3, 10])

    def test_email_is_checked(self):
        with self.assertRaises(ValidationError):
            StudentMember(1, "Mg Mg", "not-an-email")

    def test_limit_is_enforced(self):
        student = StudentMember(1, "Mg Mg", "mgmg@gmail.com")
        for number in range(1, 5):
            student.add_borrowed_book(Book(number, f"Book {number}", "A", "C"))
        self.assertEqual(student.borrowed_count(), 3)
        self.assertTrue(student.has_reached_limit())

    def test_encapsulation(self):
        student = StudentMember(1, "Mg Mg", "mgmg@gmail.com")
        book = Book(1, "Python", "A", "C")
        student.add_borrowed_book(book)
        returned = student.get_borrowed_books()
        returned.clear()
        self.assertEqual(student.borrowed_count(), 1)
        self.assertFalse(hasattr(student, "__borrowed_books"))

    def test_duplicate_borrow_is_refused(self):
        student = StudentMember(1, "Mg Mg", "mgmg@gmail.com")
        book = Book(1, "Python", "A", "C")
        self.assertTrue(student.add_borrowed_book(book))
        self.assertFalse(student.add_borrowed_book(book))

    def test_only_books_can_be_borrowed(self):
        student = StudentMember(1, "Mg Mg", "mgmg@gmail.com")
        with self.assertRaises(ValidationError):
            student.add_borrowed_book("not a book")

    def test_remove_book(self):
        student = StudentMember(1, "Mg Mg", "mgmg@gmail.com")
        book = Book(1, "Python", "A", "C")
        self.assertFalse(student.remove_borrowed_book(book))
        student.add_borrowed_book(book)
        self.assertTrue(student.remove_borrowed_book(book))
        self.assertEqual(student.borrowed_count(), 0)


class TestLibrary(unittest.TestCase):
    def setUp(self):
        self.library = make_library()

    def test_add_book_and_member(self):
        self.assertTrue(self.library.add_book(Book(104, "New", "Author", "Cat")))
        self.assertEqual(len(self.library.books), 4)
        self.assertTrue(self.library.register_member(StudentMember(3, "Ma Ma", "mama@gmail.com")))
        self.assertEqual(len(self.library.members), 3)

    def test_duplicate_ids_are_refused(self):
        result = self.library.add_book(Book(101, "Copy", "Author", "Cat"))
        self.assertFalse(result)
        self.assertEqual(len(self.library.books), 3)

    def test_borrow_and_return(self):
        result = self.library.borrow_book(1, 101)
        self.assertTrue(result)
        self.assertFalse(self.library.find_book(101).is_available)
        self.assertTrue(self.library.find_member(1).has_borrowed(self.library.find_book(101)))

        self.assertTrue(self.library.return_book(1, 101))
        self.assertTrue(self.library.find_book(101).is_available)
        self.assertEqual(self.library.find_member(1).borrowed_count(), 0)

    def test_borrow_unknown_member_or_book(self):
        self.assertFalse(self.library.borrow_book(99, 101))
        self.assertFalse(self.library.borrow_book(1, 999))

    def test_book_cannot_be_borrowed_twice(self):
        self.library.borrow_book(1, 101)
        result = self.library.borrow_book(2, 101)
        self.assertFalse(result)
        self.assertIn("already borrowed", result.message)

    def test_same_member_cannot_take_one_book_twice(self):
        self.library.borrow_book(1, 101)
        self.assertFalse(self.library.borrow_book(1, 101))

    def test_student_limit(self):
        self.library.add_book(Book(104, "Refactoring", "Martin Fowler", "Programming"))
        for book_id in (101, 102, 103):
            self.assertTrue(self.library.borrow_book(1, book_id))
        result = self.library.borrow_book(1, 104)
        self.assertFalse(result)
        self.assertIn("limit", result.message.lower())

    def test_teacher_can_borrow_more(self):
        teacher = self.library.find_member(2)
        for book_id in (101, 102, 103):
            self.assertTrue(self.library.borrow_book(2, book_id))
        self.assertEqual(teacher.borrowed_count(), 3)

    def test_return_a_book_the_member_never_had(self):
        result = self.library.return_book(1, 101)
        self.assertFalse(result)
        self.assertIn("did not borrow", result.message)

    def test_cannot_remove_a_borrowed_book(self):
        self.library.borrow_book(1, 101)
        self.assertFalse(self.library.remove_book(101))
        self.assertTrue(self.library.remove_book(102))

    def test_cannot_remove_a_member_with_books(self):
        self.library.borrow_book(1, 101)
        self.assertFalse(self.library.remove_member(1))
        self.assertTrue(self.library.remove_member(2))

    def test_search(self):
        self.assertEqual(len(self.library.find_books("Robert")), 2)
        self.assertEqual(len(self.library.find_books("python")), 1)
        self.assertEqual(len(self.library.find_books("programming")), 2)
        self.assertEqual(len(self.library.find_books("zzz")), 0)

    def test_statistics(self):
        self.library.borrow_book(1, 101)
        self.library.borrow_book(2, 102)
        stats = self.library.statistics()
        self.assertEqual(stats["total_books"], 3)
        self.assertEqual(stats["available_books"], 1)
        self.assertEqual(stats["borrowed_books"], 2)
        self.assertEqual(stats["borrowed_by_type"], {"Student": 1, "Teacher": 1})

    def test_bad_ids_do_not_crash_lookup(self):
        self.assertIsNone(self.library.find_book("abc"))
        self.assertIsNone(self.library.find_member(None))


class TestJsonStorage(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.storage = LibraryStorage(self.folder)
        self.library = make_library()
        self.library.storage = self.storage

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_round_trip(self):
        self.library.borrow_book(1, 101)
        self.library.save()

        self.assertTrue((self.folder / "books.json").exists())
        self.assertTrue((self.folder / "members.json").exists())

        reloaded = Library("Test Library", storage=self.storage)
        reloaded.load()

        self.assertEqual(len(reloaded.books), 3)
        self.assertEqual(len(reloaded.members), 2)
        self.assertFalse(reloaded.find_book(101).is_available)
        self.assertEqual(reloaded.find_member(1).borrowed_count(), 1)
        self.assertIsInstance(reloaded.find_member(1), StudentMember)
        self.assertIsInstance(reloaded.find_member(2), TeacherMember)

    def test_json_shape(self):
        self.library.save()
        records = json.loads((self.folder / "books.json").read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(records[0]),
            ["author", "book_id", "category", "is_available", "title"],
        )
        members = json.loads((self.folder / "members.json").read_text(encoding="utf-8"))
        self.assertIn("borrowed_book_ids", members[0])
        self.assertIn("member_type", members[0])

    def test_missing_folder_is_created(self):
        nested = self.folder / "deep" / "data"
        storage = LibraryStorage(nested)
        storage.save_books([Book(1, "A", "B", "C")])
        self.assertTrue((nested / "books.json").exists())

    def test_damaged_file_does_not_crash(self):
        (self.folder / "books.json").write_text("{ not json", encoding="utf-8")
        self.assertEqual(self.storage.load_books(), [])
        self.assertEqual(self.storage.load_members(), [])

    def test_empty_files_are_seeded(self):
        storage = LibraryStorage(self.folder / "fresh")
        library = Library("Fresh", storage=storage)
        library.load()
        self.assertTrue(library.books)
        self.assertTrue(library.members)

    def test_broken_record_is_skipped(self):
        (self.folder / "books.json").write_text(
            json.dumps([{"title": "No id"}, {"book_id": 1, "title": "A", "author": "B"}]),
            encoding="utf-8",
        )
        books = self.storage.load_books()
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].book_id, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
