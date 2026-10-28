"""Gestion des comptes (réservée aux administrateurs)."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..db import get_session
from ..models import USER_ROLES, Member, User
from ..security import admin_only, hash_password
from ..web import b, flash, i, redirect, render, s

router = APIRouter(prefix="/users")


def members_list(session: Session):
    return session.exec(select(Member).order_by(Member.nickname)).all()


@router.get("")
def list_users(request: Request, user: User = Depends(admin_only), session: Session = Depends(get_session)):
    users = session.exec(select(User).where(User.pending == False).order_by(User.name)).all()  # noqa: E712
    members = {m.id: m for m in members_list(session)}
    return render(request, "users/list.html", users=users, members=members)


@router.get("/new")
def new_user(request: Request, user: User = Depends(admin_only), session: Session = Depends(get_session)):
    return render(request, "users/form.html", item=None, members=members_list(session))


@router.get("/{user_id}/edit")
def edit_user(user_id: int, request: Request, user: User = Depends(admin_only),
              session: Session = Depends(get_session)):
    item = session.get(User, user_id) or _404()
    return render(request, "users/form.html", item=item, members=members_list(session))


@router.post("/new")
@router.post("/{user_id}/edit")
async def save_user(request: Request, user_id: int | None = None, user: User = Depends(admin_only),
                    session: Session = Depends(get_session)):
    form = await request.form()
    item = session.get(User, user_id) if user_id else User(name="", email="", password_hash="")
    if user_id and not item:
        _404()
    email = (s(form, "email") or "").lower()
    duplicate = session.exec(select(User).where(User.email == email, User.id != item.id)).first()
    if not email or not s(form, "name") or duplicate:
        flash(request, "Nom et e-mail obligatoires, et l'e-mail ne doit pas déjà exister.", "error")
        return render(request, "users/form.html", item=item, members=members_list(session))

    item.name, item.email = s(form, "name"), email
    role = s(form, "role") or "staff"
    item.role = role if role in USER_ROLES else "staff"
    item.member_id = i(form, "member_id")
    item.active = b(form, "active") if user_id else True
    if item.id == user.id:  # on ne peut pas se retirer ses propres droits
        item.role, item.active = "admin", True

    password = form.get("password") or ""
    generated = None
    if not user_id and not password:
        generated = password = secrets.token_urlsafe(9)
    if password:
        item.password_hash = hash_password(password)

    session.add(item)
    session.commit()
    if generated:
        flash(request, f"Compte créé. Mot de passe provisoire pour {email} : {generated}", "info")
    else:
        flash(request, "Compte enregistré.")
    return redirect("/users")


def _404():
    raise HTTPException(404)
