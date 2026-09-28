"""TeacherMember: a Member with a larger borrowing limit."""

from .member import Member


class TeacherMember(Member):
    """A teacher may borrow 10 books for 28 days."""

    MEMBER_TYPE = "Teacher"
    BORROWING_LIMIT = 10
    LOAN_DAYS = 28

    def borrowing_limit(self):
        return TeacherMember.BORROWING_LIMIT

    def member_type(self):
        return TeacherMember.MEMBER_TYPE

    def loan_days(self):
        return TeacherMember.LOAN_DAYS
