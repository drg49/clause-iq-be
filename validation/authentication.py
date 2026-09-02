import re
from models.user import Users


# -----------------------------
# EMAIL
# -----------------------------
EMAIL_REGEX = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'


def validate_email(email):
    if not email or not isinstance(email, str):
        return False, 'Email is required.'

    email = email.strip().lower()

    if len(email) < 3 or len(email) > 150:
        return False, 'Email must be between 3 and 150 characters.'

    if not re.match(EMAIL_REGEX, email):
        return False, 'Invalid email address.'

    if Users.query.filter_by(email=email).first():
        return False, 'Email already registered.'

    return True, ''


# -----------------------------
# PASSWORD (STRONGER)
# -----------------------------
def validate_password(password):
    if not password or not isinstance(password, str):
        return False, 'Password is required.'

    if len(password) < 8:
        return False, 'Password must be at least 8 characters long.'

    if len(password) > 255:
        return False, 'Password exceeds 255 character limit.'

    return True, ''


# -----------------------------
# FIRST NAME
# -----------------------------
NAME_REGEX = r"^[A-Za-zÀ-ÖØ-öø-ÿ'\- ]{2,25}$"


def validate_first_name(first_name):
    if not first_name or not isinstance(first_name, str):
        return False, 'First name is required.'

    first_name = first_name.strip()

    if len(first_name) < 2 or len(first_name) > 25:
        return False, 'First name must be between 2 and 25 characters.'

    if not re.match(NAME_REGEX, first_name):
        return False, 'First name can only contain letters, spaces, hyphens, and apostrophes.'

    return True, ''


# -----------------------------
# LAST NAME
# -----------------------------
def validate_last_name(last_name):
    if not last_name or not isinstance(last_name, str):
        return False, 'Last name is required.'

    last_name = last_name.strip()

    if len(last_name) < 2 or len(last_name) > 25:
        return False, 'Last name must be between 2 and 25 characters.'

    if not re.match(NAME_REGEX, last_name):
        return False, 'Last name can only contain letters, spaces, hyphens, and apostrophes.'

    return True, ''