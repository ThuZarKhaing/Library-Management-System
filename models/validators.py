"""Small input helpers shared by the model classes.

Keeping the validation in one place means every class gives the same kind of
error message, and the classes themselves stay focused on their own data.
"""

import re

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class ValidationError(ValueError):
    """Raised when data typed by a user cannot be used."""


def clean_text(value, field_name, allow_empty=False):
    """Return the value as a trimmed string."""
    if value is None:
        raise ValidationError(f"{field_name} is required.")
    text = str(value).strip()
    if not text and not allow_empty:
        raise ValidationError(f"{field_name} is required.")
    return text


def clean_id(value, field_name):
    """Return the value as a non negative whole number."""
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a whole number.") from None
    if number < 0:
        raise ValidationError(f"{field_name} cannot be negative.")
    return number


def clean_email(value):
    """Return a lowercase, trimmed and checked email address."""
    email = clean_text(value, "Email").lower()
    if not EMAIL_PATTERN.match(email):
        raise ValidationError(f"'{value}' is not a valid email address.")
    return email
