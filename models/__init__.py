"""The model package: Book, Member and the two member subclasses.

``member_from_dict`` is the factory used by the JSON storage layer.  It cannot
live in ``member.py`` because that module would then have to import its own
subclasses.
"""

from .book import Book
from .member import Member
from .student import StudentMember
from .teacher import TeacherMember
from .user import User
from .validators import ValidationError

MEMBER_CLASSES = {
    Member.MEMBER_TYPE: Member,
    StudentMember.MEMBER_TYPE: StudentMember,
    TeacherMember.MEMBER_TYPE: TeacherMember,
}

__all__ = [
    "Book",
    "Member",
    "StudentMember",
    "TeacherMember",
    "User",
    "ValidationError",
    "MEMBER_CLASSES",
    "member_from_dict",
]


def member_from_dict(data, book_lookup=None):
    """Create the right Member subclass from a saved JSON record."""
    member_class = MEMBER_CLASSES.get(data.get("member_type", Member.MEMBER_TYPE), Member)
    return member_class.from_dict(data, book_lookup=book_lookup)
