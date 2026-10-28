"""Templates, filtres d'affichage et petits utilitaires pour les formulaires."""

import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from . import models

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MONTHS_FULL = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
               "septembre", "octobre", "novembre", "décembre"]
DAYS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def fmt_date(value) -> str:
    if not value:
        return "—"
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def fmt_datetime(value) -> str:
    if not value:
        return "—"
    return f"{DAYS[value.weekday()]} {value.day} {MONTHS[value.month - 1]} · {value:%H:%M}"


def fmt_money(value) -> str:
    value = value or 0
    text = f"{abs(value):,.2f}".replace(",", " ").replace(".", ",")
    if text.endswith(",00"):
        text = text[:-3]
    return f"{'-' if value < 0 else ''}{text} €"


def age(birth: Optional[date]) -> Optional[int]:
    if not birth:
        return None
    today = date.today()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


templates.env.filters.update(d=fmt_date, dt=fmt_datetime, money=fmt_money, age=age)
templates.env.globals.update(
    GAMES=models.GAMES,
    GAME_STATS=models.GAME_STATS,
    GAME_ROLES=models.GAME_ROLES,
    USER_ROLES=models.USER_ROLES,
    MEMBER_KINDS=models.MEMBER_KINDS,
    MEMBER_STATUS=models.MEMBER_STATUS,
    CONTRACT_TYPES=models.CONTRACT_TYPES,
    EVENT_KINDS=models.EVENT_KINDS,
    TRANSACTION_CATEGORIES=models.TRANSACTION_CATEGORIES,
    SPONSOR_STATUS=models.SPONSOR_STATUS,
    MONTHS_FULL=MONTHS_FULL,
    today=date.today,
    now=datetime.now,
    ORG_NAME=os.environ.get("STRUCTURE_NAME", "Ma structure"),
)


def render(request: Request, name: str, **context):
    context.setdefault("user", getattr(request.state, "user", None))
    user = context["user"]
    if user and user.role in ("admin", "staff"):
        from sqlmodel import Session, func, select
        from .db import engine
        with Session(engine) as session:
            context["pending_count"] = session.exec(
                select(func.count()).select_from(models.User).where(models.User.pending)).one()
    context["signup_enabled"] = os.environ.get("ALLOW_SIGNUP", "1") not in ("0", "false", "non")
    context["flashes"] = request.session.pop("flashes", [])
    context["path"] = request.url.path
    return templates.TemplateResponse(request, name, context)


def flash(request: Request, message: str, kind: str = "ok") -> None:
    request.session.setdefault("flashes", []).append({"message": message, "kind": kind})


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


# --- Lecture des champs de formulaire ---------------------------------------


def s(form, key: str) -> Optional[str]:
    value = (form.get(key) or "").strip()
    return value or None


def i(form, key: str) -> Optional[int]:
    value = s(form, key)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def f(form, key: str) -> Optional[float]:
    value = s(form, key)
    try:
        return float(value.replace(",", ".").replace(" ", "")) if value is not None else None
    except ValueError:
        return None


def d(form, key: str) -> Optional[date]:
    value = s(form, key)
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def dt(form, key: str) -> Optional[datetime]:
    value = s(form, key)
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def b(form, key: str) -> bool:
    return form.get(key) in ("on", "1", "true", "yes")
