"""Membres de la structure (joueurs, staff) et leurs contrats."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..db import get_session
from ..models import (CONTRACT_TYPES, MEMBER_KINDS, MEMBER_STATUS, Contract, Event, Member,
                      PlayerStat, Team, User)
from ..security import any_user, staff_only
from ..web import d, f, flash, i, redirect, render, s
from .dashboard import visible_team_ids

router = APIRouter(prefix="/members")


def teams_list(session):
    return session.exec(select(Team).order_by(Team.active.desc(), Team.name)).all()


@router.get("")
def list_members(request: Request, team: int | None = None, kind: str | None = None, status: str | None = None,
                 user: User = Depends(any_user), session: Session = Depends(get_session)):
    q = select(Member).order_by(Member.nickname)
    ids = visible_team_ids(user, session)
    if ids is not None:
        q = q.where(Member.team_id.in_(ids))
    if team:
        q = q.where(Member.team_id == team)
    if kind:
        q = q.where(Member.kind == kind)
    status = status if status is not None else "actifs"
    if status == "actifs":
        q = q.where(Member.status != "inactif")
    elif status in MEMBER_STATUS:
        q = q.where(Member.status == status)
    members = session.exec(q).all()
    teams = {t.id: t for t in teams_list(session)}

    # Contrat en cours de chaque membre (staff seulement)
    current = {}
    if user.role != "joueur":
        today = date.today()
        for c in session.exec(select(Contract).order_by(Contract.start_date)).all():
            if c.start_date <= today and (c.end_date is None or c.end_date >= today):
                current[c.member_id] = c
    return render(request, "members/list.html", members=members, teams=teams, current=current,
                  filters=dict(team=team, kind=kind, status=status))


@router.get("/new")
def new_member(request: Request, team: int | None = None, user: User = Depends(staff_only),
               session: Session = Depends(get_session)):
    return render(request, "members/form.html", item=Member(nickname="", team_id=team), is_new=True,
                  teams=teams_list(session))


@router.get("/{member_id}/edit")
def edit_member(member_id: int, request: Request, user: User = Depends(staff_only),
                session: Session = Depends(get_session)):
    return render(request, "members/form.html", item=_get(session, member_id), is_new=False,
                  teams=teams_list(session))


@router.post("/new")
@router.post("/{member_id}/edit")
async def save_member(request: Request, member_id: int | None = None, user: User = Depends(staff_only),
                      session: Session = Depends(get_session)):
    form = await request.form()
    item = _get(session, member_id) if member_id else Member(nickname="")
    item.nickname = s(form, "nickname") or "Sans pseudo"
    item.first_name, item.last_name = s(form, "first_name"), s(form, "last_name")
    item.kind = s(form, "kind") if s(form, "kind") in MEMBER_KINDS else "joueur"
    item.status = s(form, "status") if s(form, "status") in MEMBER_STATUS else "actif"
    item.game_role = s(form, "game_role")
    item.team_id = i(form, "team_id")
    item.email, item.phone, item.discord = s(form, "email"), s(form, "phone"), s(form, "discord")
    item.nationality = s(form, "nationality")
    item.birth_date, item.joined_on = d(form, "birth_date"), d(form, "joined_on")
    item.notes = s(form, "notes")
    session.add(item)
    session.commit()
    flash(request, "Membre enregistré.")
    return redirect(f"/members/{item.id}")


@router.get("/{member_id}")
def member_detail(member_id: int, request: Request, user: User = Depends(any_user),
                  session: Session = Depends(get_session)):
    member = _get(session, member_id)
    ids = visible_team_ids(user, session)
    if ids is not None and member.team_id not in ids:
        raise HTTPException(404)
    team = session.get(Team, member.team_id) if member.team_id else None
    contracts = []
    if user.role != "joueur" or user.member_id == member.id:
        contracts = session.exec(select(Contract).where(Contract.member_id == member.id)
                                 .order_by(Contract.start_date.desc())).all()
    stats = session.exec(
        select(PlayerStat, Event).join(Event, Event.id == PlayerStat.event_id)
        .where(PlayerStat.member_id == member.id).order_by(Event.starts_at.desc())
    ).all()
    return render(request, "members/detail.html", member=member, team=team, contracts=contracts,
                  stats=stats, today=date.today())


# --- Contrats ---------------------------------------------------------------


@router.get("/{member_id}/contracts/new")
def new_contract(member_id: int, request: Request, user: User = Depends(staff_only),
                 session: Session = Depends(get_session)):
    return render(request, "members/contract_form.html", member=_get(session, member_id), item=None)


@router.get("/{member_id}/contracts/{contract_id}/edit")
def edit_contract(member_id: int, contract_id: int, request: Request, user: User = Depends(staff_only),
                  session: Session = Depends(get_session)):
    item = session.get(Contract, contract_id)
    if not item or item.member_id != member_id:
        raise HTTPException(404)
    return render(request, "members/contract_form.html", member=_get(session, member_id), item=item)


@router.post("/{member_id}/contracts/new")
@router.post("/{member_id}/contracts/{contract_id}/edit")
async def save_contract(member_id: int, request: Request, contract_id: int | None = None,
                        user: User = Depends(staff_only), session: Session = Depends(get_session)):
    member = _get(session, member_id)
    form = await request.form()
    item = session.get(Contract, contract_id) if contract_id else Contract(member_id=member.id,
                                                                          start_date=date.today())
    if not item or item.member_id != member.id:
        raise HTTPException(404)
    item.type = s(form, "type") if s(form, "type") in CONTRACT_TYPES else "salarie"
    item.start_date = d(form, "start_date") or date.today()
    item.end_date = d(form, "end_date")
    item.monthly_amount = f(form, "monthly_amount") or 0
    item.notes = s(form, "notes")
    if item.end_date and item.end_date < item.start_date:
        flash(request, "La date de fin doit être après la date de début.", "error")
        return render(request, "members/contract_form.html", member=member, item=item)
    session.add(item)
    session.commit()
    flash(request, "Contrat enregistré.")
    return redirect(f"/members/{member.id}")


@router.post("/{member_id}/contracts/{contract_id}/delete")
def delete_contract(member_id: int, contract_id: int, request: Request, user: User = Depends(staff_only),
                    session: Session = Depends(get_session)):
    item = session.get(Contract, contract_id)
    if item and item.member_id == member_id:
        session.delete(item)
        session.commit()
        flash(request, "Contrat supprimé.")
    return redirect(f"/members/{member_id}")


def _get(session, member_id):
    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(404)
    return member
