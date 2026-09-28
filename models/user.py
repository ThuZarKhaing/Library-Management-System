"""A staff account for the web dashboard.

The password is never stored: only a hash and the salt that produced it.  Both
are saved together in ``password_hash`` as ``method$salt$hash``, so the format
can be changed later without breaking old files.
"""

import hashlib
import hmac
import os

from .validators import clean_text

SALT_BYTES = 16
HASH_ROUNDS = 240_000
ALGORITHM = "pbkdf2_sha256"


class User:
    """Someone who can sign in: an ``admin`` or a member of ``staff``."""

    ADMIN = "admin"
    STAFF = "staff"
    ROLES = (ADMIN, STAFF)

    def __init__(self, username, password_hash, role=STAFF, full_name=""):
        self.username = clean_text(username, "Username").lower()
        if not User.role_is_valid(role):
            raise ValueError(f"Role must be one of: {', '.join(User.ROLES)}.")
        self.password_hash = clean_text(password_hash, "Password hash")
        self.role = role
        self.full_name = clean_text(full_name, "Full name", allow_empty=True)

    # ------------------------------------------------------------------ roles
    @staticmethod
    def role_is_valid(role):
        return role in User.ROLES

    @property
    def is_admin(self):
        return self.role == self.ADMIN

    @property
    def is_staff(self):
        return self.role == self.STAFF

    @property
    def role_label(self):
        return "Administrator" if self.is_admin else "Staff"

    # -------------------------------------------------------------- passwords
    @classmethod
    def hash_password(cls, password):
        """Return ``method$salt$hash`` for a plain password."""
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        salt = os.urandom(SALT_BYTES).hex()
        return f"{ALGORITHM}${salt}${cls._derive(password, salt)}"

    @staticmethod
    def _derive(password, salt):
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), HASH_ROUNDS
        )
        return digest.hex()

    def check_password(self, password):
        """Constant-time check of a plain password against the stored hash."""
        try:
            algorithm, salt, expected = self.password_hash.split("$")
            if algorithm != ALGORITHM:
                return False
        except ValueError:
            return False
        if not password:
            return False
        return hmac.compare_digest(self._derive(password, salt), expected)

    def set_password(self, password):
        self.password_hash = self.hash_password(password)

    # ------------------------------------------------------------ json (storage)
    def to_dict(self):
        return {
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "password_hash": self.password_hash,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            username=data["username"],
            password_hash=data.get("password_hash", ""),
            role=data.get("role", cls.STAFF),
            full_name=data.get("full_name", ""),
        )

    @classmethod
    def create(cls, username, password, role=STAFF, full_name=""):
        """Build a new account with the password hashed."""
        return cls(username, cls.hash_password(password), role=role, full_name=full_name)

    # ---------------------------------------------------------- dunder methods
    def __str__(self):
        return f"{self.full_name or self.username} ({self.role_label})"

    def __repr__(self):
        return f"User(username={self.username!r}, role={self.role!r})"
