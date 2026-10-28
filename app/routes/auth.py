"""Connexion, déconnexion et création du premier compte administrateur."""

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, func, select

from ..db import get_session
from ..models import User
from ..security import any_user, hash_password, verify_password
from ..web import flash, redirect, render, s

router = APIRouter()


def has_users(session: Session) -> bool:
    return session.exec(select(func.count()).select_from(User)).one() > 0


@router.get("/login")
def login_page(request: Request, session: Session = Depends(get_session)):
    if not has_users(session):
        return redirect("/setup")
    if getattr(request.state, "user", None) or request.session.get("user_id"):
        user = session.get(User, request.session.get("user_id"))
        if user and user.active:
            return redirect("/")
    return render(request, "login.html")


@router.post("/login")
async def login(request: Request, session: Session = Depends(get_session)):
    form = await request.form()
    email = (s(form, "email") or "").lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(form.get("password") or "", user.password_hash):
        return render(request, "login.html", error="E-mail ou mot de passe incorrect.", email=email)
    if user.pending:
        return render(request, "login.html", email=email,
                      error="Ton inscription est en attente de validation par le staff. Réessaie plus tard.")
    if not user.active:
        return render(request, "login.html", error="Ce compte est désactivé.", email=email)
    request.session.clear()
    request.session["user_id"] = user.id
    return redirect("/")


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/login")


@router.get("/setup")
def setup_page(request: Request, session: Session = Depends(get_session)):
    if has_users(session):
        return redirect("/login")
    return render(request, "setup.html")


@router.post("/setup")
async def setup(request: Request, session: Session = Depends(get_session)):
    if has_users(session):
        return redirect("/login")
    form = await request.form()
    name, email, password = s(form, "name"), (s(form, "email") or "").lower(), form.get("password") or ""
    if not name or not email or len(password) < 8:
        return render(request, "setup.html", error="Remplis tous les champs (mot de passe : 8 caractères minimum).",
                      name=name, email=email)
    user = User(name=name, email=email, password_hash=hash_password(password), role="admin")
    session.add(user)
    session.commit()
    request.session["user_id"] = user.id
    flash(request, "Compte administrateur créé. Bienvenue !")
    return redirect("/")


@router.get("/account")
def account_page(request: Request, user: User = Depends(any_user)):
    return render(request, "account.html")


@router.post("/account")
async def account_update(request: Request, user: User = Depends(any_user),
                         session: Session = Depends(get_session)):
    form = await request.form()
    current, new = form.get("current") or "", form.get("new") or ""
    if not verify_password(current, user.password_hash):
        return render(request, "account.html", error="Mot de passe actuel incorrect.")
    if len(new) < 8:
        return render(request, "account.html", error="Le nouveau mot de passe doit faire au moins 8 caractères.")
    user.password_hash = hash_password(new)
    session.add(user)
    session.commit()
    flash(request, "Mot de passe modifié.")
    return redirect("/account")
