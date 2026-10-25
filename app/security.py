"""Mots de passe, session et contrôle des droits."""

import hashlib
import hmac
import os
import secrets

from fastapi import Depends, Request
from sqlmodel import Session

from .db import DATA_DIR, get_session
from .models import User

ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return f"pbkdf2${ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(check, digest)


def secret_key() -> str:
    """Clé de signature des sessions, générée une fois et gardée dans data/."""
    if os.environ.get("APP_SECRET_KEY"):
        return os.environ["APP_SECRET_KEY"]
    path = DATA_DIR / "secret.key"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48))
        path.chmod(0o600)
    return path.read_text().strip()


class LoginRequired(Exception):
    pass


class Forbidden(Exception):
    pass


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None
    if not user or not user.active:
        request.session.clear()
        raise LoginRequired()
    request.state.user = user
    return user


def require(*roles: str):
    """Dépendance : l'utilisateur connecté doit avoir un de ces rôles."""

    def checker(user: User = Depends(current_user)) -> User:
        if roles and user.role not in roles:
            raise Forbidden()
        return user

    return checker


# Raccourcis
any_user = require()
staff_only = require("admin", "staff")
admin_only = require("admin")
