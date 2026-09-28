"""What each role is allowed to do.

The rules are written once, as data, so a route can ask
``can(current_user.role, "delete_book")`` instead of repeating
``if current_user.is_admin`` in a dozen places.
"""

from models import User

# capability -> the roles that have it
CAPABILITIES = {
    "view_dashboard": (User.ADMIN, User.STAFF),
    "view_books": (User.ADMIN, User.STAFF),
    "add_book": (User.ADMIN, User.STAFF),
    "edit_book": (User.ADMIN, User.STAFF),
    "delete_book": (User.ADMIN,),
    "view_members": (User.ADMIN, User.STAFF),
    "add_member": (User.ADMIN, User.STAFF),
    "edit_member": (User.ADMIN, User.STAFF),
    "delete_member": (User.ADMIN,),
    "borrow_book": (User.ADMIN, User.STAFF),
    "return_book": (User.ADMIN, User.STAFF),
    "view_users": (User.ADMIN,),
    "manage_users": (User.ADMIN,),
}

CAPABILITY_LABELS = {
    "view_dashboard": "Open the dashboard",
    "view_books": "Browse the catalogue",
    "add_book": "Add a book",
    "edit_book": "Edit a book",
    "delete_book": "Delete a book",
    "view_members": "Browse the members",
    "add_member": "Register a member",
    "edit_member": "Edit a member",
    "delete_member": "Delete a member",
    "borrow_book": "Borrow a book",
    "return_book": "Return a book",
    "view_users": "See the staff accounts",
    "manage_users": "Create, edit and delete staff accounts",
}


def can(role, capability):
    """True when ``role`` is allowed to perform ``capability``."""
    allowed = CAPABILITIES.get(capability)
    if allowed is None:
        raise KeyError(f"Unknown capability: {capability!r}")
    return role in allowed


def capabilities_for(role):
    """Every capability a role has, as a set of names."""
    return {name for name, roles in CAPABILITIES.items() if role in roles}


def matrix():
    """The whole permission table, for the help page and for tests."""
    return {name: set(roles) for name, roles in CAPABILITIES.items()}
