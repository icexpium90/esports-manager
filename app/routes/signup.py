"""Inscription en ligne des joueurs, puis validation par le staff."""

import os
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, func, select

from ..db import get_session
from ..models import PENDING, Contract, Member, PlayerStat, Team, User
from ..security import hash_password, staff_only
from ..web import d, flash, i, redirect, render, s

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def signup_enabled() -> bool:
    return os.environ.get("ALLOW_SIGNUP", "1") not in ("0", "false", "non")


def active_teams(session: Session):
    return session.exec(select(Team).where(Team.active).order_by(Team.game, Team.name)).all()


@router.get("/register")
def register_page(request: Request, session: Session = Depends(get_session)):
    if not signup_enabled():
        raise HTTPException(404)
    if not session.exec(select(func.count()).select_from(User)).one():
        return redirect("/setup")
    return render(request, "register.html", teams=active_teams(session), form={})


@router.post("/register")
async def register(request: Request, session: Session = Depends(get_session)):
    if not signup_enabled():
        raise HTTPException(404)
    form = await request.form()
    if s(form, "website"):  # champ piège invisible : rempli uniquement par les robots
        return render(request, "register_done.html")

    data = {k: s(form, k) or "" for k in ("nickname", "first_name", "last_name", "email", "discord",
                                          "game_role", "team_id", "birth_date")}
    email = data["email"].lower()
    password, password2 = form.get("password") or "", form.get("password2") or ""
    errors = []
    if not data["nickname"]:
        errors.append("Le pseudo est obligatoire.")
    if not EMAIL_RE.match(email):
        errors.append("L'adresse e-mail n'est pas valide.")
    elif session.exec(select(User).where(User.email == email)).first():
        errors.append("Un compte existe déjà avec cette adresse e-mail.")
    if not data["discord"]:
        errors.append("Ton pseudo Discord est obligatoire (pour que le staff puisse te contacter).")
    if len(password) < 8:
        errors.append("Le mot de passe doit faire au moins 8 caractères.")
    elif password != password2:
        errors.append("Les deux mots de passe ne correspondent pas.")
    team_id = i(form, "team_id")
    team = session.get(Team, team_id) if team_id else None
    if team_id and (not team or not team.active):
        errors.append("Équipe inconnue.")
    if errors:
        return render(request, "register.html", teams=active_teams(session), form=data, errors=errors)

    member = Member(nickname=data["nickname"], first_name=data["first_name"] or None,
                    last_name=data["last_name"] or None, email=email, discord=data["discord"],
                    game_role=data["game_role"] or None, team_id=team.id if team else None,
                    birth_date=d(form, "birth_date"), kind="joueur", status=PENDING)
    session.add(member)
    session.commit()
    name = " ".join(x for x in (member.first_name, member.last_name) if x) or member.nickname
    session.add(User(name=name, email=email, password_hash=hash_password(password), role="joueur",
                     member_id=member.id, active=False, pending=True))
    session.commit()
    return render(request, "register_done.html", nickname=member.nickname)


# --- Validation par le staff ------------------------------------------------


def pending_requests(session: Session):
    return session.exec(select(User, Member).join(Member, Member.id == User.member_id, isouter=True)
                        .where(User.pending).order_by(User.created_at)).all()


@router.get("/signups")
def signups(request: Request, user: User = Depends(staff_only), session: Session = Depends(get_session)):
    return render(request, "signups.html", requests=pending_requests(session),
                  teams=session.exec(select(Team).where(Team.active).order_by(Team.name)).all())


def _pending(session: Session, user_id: int) -> User:
    account = session.get(User, user_id)
    if not account or not account.pending:
        raise HTTPException(404)
    return account


@router.post("/signups/{user_id}/approve")
async def approve(user_id: int, request: Request, user: User = Depends(staff_only),
                  session: Session = Depends(get_session)):
    account = _pending(session, user_id)
    form = await request.form()
    member = session.get(Member, account.member_id) if account.member_id else None
    if member:
        member.team_id = i(form, "team_id")
        member.kind = s(form, "kind") if s(form, "kind") in ("joueur", "remplacant") else "joueur"
        member.status = s(form, "status") if s(form, "status") in ("actif", "essai") else "essai"
        member.joined_on = member.joined_on or date.today()
        session.add(member)
    account.pending, account.active, account.role = False, True, "joueur"
    session.add(account)
    session.commit()
    flash(request, f"Inscription de {member.nickname if member else account.name} validée : il peut se connecter.")
    return redirect("/signups")


@router.post("/signups/{user_id}/reject")
def reject(user_id: int, request: Request, user: User = Depends(staff_only),
           session: Session = Depends(get_session)):
    account = _pending(session, user_id)
    member = session.get(Member, account.member_id) if account.member_id else None
    label = member.nickname if member else account.name
    session.delete(account)
    session.commit()
    if member and member.status == PENDING:
        has_history = session.exec(select(Contract).where(Contract.member_id == member.id)).first() or \
            session.exec(select(PlayerStat).where(PlayerStat.member_id == member.id)).first()
        if not has_history:
            session.delete(member)
            session.commit()
    flash(request, f"Inscription de {label} refusée et supprimée.")
    return redirect("/signups")
