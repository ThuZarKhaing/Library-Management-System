"""StudentMember: a Member with a smaller borrowing limit."""

from .member import Member


class StudentMember(Member):
    """A student may borrow 3 books for 14 days."""

    MEMBER_TYPE = "Student"
    BORROWING_LIMIT = 3
    LOAN_DAYS = 14

    def borrowing_limit(self):
        return StudentMember.BORROWING_LIMIT

    def member_type(self):
        return StudentMember.MEMBER_TYPE

    def loan_days(self):
        return StudentMember.LOAN_DAYS
