"""Équipes (une par jeu / line-up)."""

from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..db import get_session
from ..models import GAMES, Event, Member, PlayerStat, Team, User
from ..security import any_user, staff_only
from ..web import b, flash, redirect, render, s
from .dashboard import visible_team_ids

router = APIRouter(prefix="/teams")


def team_record(events):
    w = l = dr = 0
    for e in events:
        if e.score_us is None or e.score_them is None:
            continue
        if e.score_us > e.score_them:
            w += 1
        elif e.score_us < e.score_them:
            l += 1
        else:
            dr += 1
    return w, l, dr


@router.get("")
def list_teams(request: Request, user: User = Depends(any_user), session: Session = Depends(get_session)):
    q = select(Team).order_by(Team.active.desc(), Team.game, Team.name)
    ids = visible_team_ids(user, session)
    if ids is not None:
        q = q.where(Team.id.in_(ids))
    teams = session.exec(q).all()
    members = session.exec(select(Member).where(Member.status != "inactif")).all()
    counts = defaultdict(int)
    for m in members:
        if m.team_id:
            counts[m.team_id] += 1
    records = {}
    for t in teams:
        evs = session.exec(select(Event).where(Event.team_id == t.id, Event.kind == "officiel")).all()
        records[t.id] = team_record(evs)
    return render(request, "teams/list.html", teams=teams, counts=counts, records=records)


@router.get("/new")
def new_team(request: Request, user: User = Depends(staff_only)):
    return render(request, "teams/form.html", item=None)


@router.get("/{team_id}/edit")
def edit_team(team_id: int, request: Request, user: User = Depends(staff_only),
              session: Session = Depends(get_session)):
    return render(request, "teams/form.html", item=_get(session, team_id))


@router.post("/new")
@router.post("/{team_id}/edit")
async def save_team(request: Request, team_id: int | None = None, user: User = Depends(staff_only),
                    session: Session = Depends(get_session)):
    form = await request.form()
    item = _get(session, team_id) if team_id else Team(name="", game="valorant")
    item.name = s(form, "name") or "Sans nom"
    item.game = s(form, "game") if s(form, "game") in GAMES else "valorant"
    item.description = s(form, "description")
    item.active = b(form, "active") if team_id else True
    session.add(item)
    session.commit()
    flash(request, "Équipe enregistrée.")
    return redirect(f"/teams/{item.id}")


@router.get("/{team_id}")
def team_detail(team_id: int, request: Request, user: User = Depends(any_user),
                session: Session = Depends(get_session)):
    team = _get(session, team_id)
    ids = visible_team_ids(user, session)
    if ids is not None and team.id not in ids:
        raise HTTPException(404)
    members = session.exec(select(Member).where(Member.team_id == team.id)
                           .order_by(Member.status, Member.kind, Member.nickname)).all()
    events = session.exec(select(Event).where(Event.team_id == team.id).order_by(Event.starts_at.desc())).all()
    now = datetime.now()
    upcoming = sorted([e for e in events if e.starts_at >= now], key=lambda e: e.starts_at)[:5]
    played = [e for e in events if e.score_us is not None and e.score_them is not None]

    # Moyennes des stats par joueur sur les matchs/scrims de l'équipe
    event_ids = [e.id for e in events]
    averages = {}
    if event_ids:
        stats = session.exec(select(PlayerStat).where(PlayerStat.event_id.in_(event_ids))).all()
        grouped = defaultdict(list)
        for st in stats:
            grouped[st.member_id].append(st)
        for mid, rows in grouped.items():
            def avg(attr):
                vals = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
                return round(sum(vals) / len(vals), 2) if vals else None
            averages[mid] = dict(games=len(rows), stat1=avg("stat1"), stat2=avg("stat2"), stat3=avg("stat3"),
                                 score=avg("score"), rating=avg("rating"), mvp=sum(1 for r in rows if r.mvp))
    return render(request, "teams/detail.html", team=team, members=members, upcoming=upcoming,
                  played=played[:10], record=team_record([e for e in played if e.kind == "officiel"]),
                  scrim_record=team_record([e for e in played if e.kind == "scrim"]), averages=averages)


def _get(session, team_id):
    team = session.get(Team, team_id)
    if not team:
        raise HTTPException(404)
    return team
