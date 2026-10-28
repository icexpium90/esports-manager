"""Calendrier : matchs, scrims, entraînements… avec résultats et stats joueurs."""

import calendar as cal
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from ..db import get_session
from ..models import EVENT_KINDS, HIDDEN_STATUSES, Event, Member, PlayerStat, Team, User
from ..security import any_user, staff_only
from ..web import b, dt, f, flash, i, redirect, render, s
from .dashboard import visible_team_ids

router = APIRouter(prefix="/calendar")


def teams_list(session):
    return session.exec(select(Team).where(Team.active).order_by(Team.name)).all()


@router.get("")
def month_view(request: Request, year: int | None = None, month: int | None = None, team: int | None = None,
               kind: str | None = None, user: User = Depends(any_user), session: Session = Depends(get_session)):
    today = date.today()
    year, month = year or today.year, month or today.month
    if not 1 <= month <= 12:
        year, month = today.year, today.month
    weeks = cal.Calendar(firstweekday=0).monthdatescalendar(year, month)
    start = datetime.combine(weeks[0][0], datetime.min.time())
    end = datetime.combine(weeks[-1][-1] + timedelta(days=1), datetime.min.time())

    q = select(Event).where(Event.starts_at >= start, Event.starts_at < end).order_by(Event.starts_at)
    ids = visible_team_ids(user, session)
    if ids is not None:
        q = q.where(Event.team_id.in_(ids))
    if team:
        q = q.where(Event.team_id == team)
    if kind:
        q = q.where(Event.kind == kind)
    by_day = {}
    for e in session.exec(q).all():
        by_day.setdefault(e.starts_at.date(), []).append(e)

    prev_m = (year - 1, 12) if month == 1 else (year, month - 1)
    next_m = (year + 1, 1) if month == 12 else (year, month + 1)
    teams = {t.id: t for t in session.exec(select(Team)).all()}
    return render(request, "events/calendar.html", weeks=weeks, by_day=by_day, year=year, month=month,
                  prev_m=prev_m, next_m=next_m, teams=teams, filters=dict(team=team, kind=kind))


@router.get("/list")
def list_view(request: Request, past: bool = False, team: int | None = None, user: User = Depends(any_user),
              session: Session = Depends(get_session)):
    now = datetime.now()
    q = select(Event)
    q = q.where(Event.starts_at < now).order_by(Event.starts_at.desc()) if past else \
        q.where(Event.starts_at >= now - timedelta(hours=3)).order_by(Event.starts_at)
    ids = visible_team_ids(user, session)
    if ids is not None:
        q = q.where(Event.team_id.in_(ids))
    if team:
        q = q.where(Event.team_id == team)
    events = session.exec(q.limit(200)).all()
    teams = {t.id: t for t in session.exec(select(Team)).all()}
    return render(request, "events/list.html", events=events, teams=teams, past=past, team=team)


@router.get("/new")
def new_event(request: Request, day: str | None = None, team: int | None = None,
              user: User = Depends(staff_only), session: Session = Depends(get_session)):
    try:
        start = datetime.fromisoformat(f"{day}T20:00") if day else None
    except ValueError:
        start = None
    item = Event(starts_at=start or datetime.now().replace(hour=20, minute=0, second=0, microsecond=0),
                 team_id=team)
    return render(request, "events/form.html", item=item, is_new=True, teams=teams_list(session))


@router.get("/{event_id}/edit")
def edit_event(event_id: int, request: Request, user: User = Depends(staff_only),
               session: Session = Depends(get_session)):
    return render(request, "events/form.html", item=_get(session, event_id), is_new=False,
                  teams=teams_list(session))


@router.post("/new")
@router.post("/{event_id}/edit")
async def save_event(request: Request, event_id: int | None = None, user: User = Depends(staff_only),
                     session: Session = Depends(get_session)):
    form = await request.form()
    item = _get(session, event_id) if event_id else Event(starts_at=datetime.now())
    item.team_id = i(form, "team_id")
    item.kind = s(form, "kind") if s(form, "kind") in EVENT_KINDS else "scrim"
    item.title, item.opponent, item.competition = s(form, "title"), s(form, "opponent"), s(form, "competition")
    item.starts_at = dt(form, "starts_at") or item.starts_at
    item.ends_at = dt(form, "ends_at")
    item.location, item.notes = s(form, "location"), s(form, "notes")
    session.add(item)
    session.commit()
    flash(request, "Événement enregistré.")
    return redirect(f"/calendar/{item.id}")


@router.post("/{event_id}/delete")
def delete_event(event_id: int, request: Request, user: User = Depends(staff_only),
                 session: Session = Depends(get_session)):
    item = _get(session, event_id)
    for st in session.exec(select(PlayerStat).where(PlayerStat.event_id == item.id)).all():
        session.delete(st)
    session.delete(item)
    session.commit()
    flash(request, "Événement supprimé.")
    return redirect("/calendar")


@router.get("/{event_id}")
def event_detail(event_id: int, request: Request, user: User = Depends(any_user),
                 session: Session = Depends(get_session)):
    event = _get(session, event_id)
    ids = visible_team_ids(user, session)
    if ids is not None and event.team_id not in ids:
        raise HTTPException(404)
    team = session.get(Team, event.team_id) if event.team_id else None
    stats = session.exec(select(PlayerStat, Member).join(Member, Member.id == PlayerStat.member_id)
                         .where(PlayerStat.event_id == event.id).order_by(Member.nickname)).all()
    return render(request, "events/detail.html", event=event, team=team, stats=stats)


# --- Résultat et stats ------------------------------------------------------


@router.get("/{event_id}/result")
def result_form(event_id: int, request: Request, user: User = Depends(staff_only),
                session: Session = Depends(get_session)):
    event = _get(session, event_id)
    team = session.get(Team, event.team_id) if event.team_id else None
    players = []
    if team:
        players = session.exec(select(Member).where(Member.team_id == team.id, Member.status.not_in(HIDDEN_STATUSES),
                                                    Member.kind.in_(["joueur", "remplacant"]))
                               .order_by(Member.kind, Member.nickname)).all()
    existing = {st.member_id: st for st in
                session.exec(select(PlayerStat).where(PlayerStat.event_id == event.id)).all()}
    # Inclure aussi d'anciens joueurs qui ont déjà des stats sur ce match
    known = {p.id for p in players}
    players += [session.get(Member, mid) for mid in existing if mid not in known]
    return render(request, "events/result.html", event=event, team=team, players=players, existing=existing)


@router.post("/{event_id}/result")
async def save_result(event_id: int, request: Request, user: User = Depends(staff_only),
                      session: Session = Depends(get_session)):
    event = _get(session, event_id)
    form = await request.form()
    event.score_us, event.score_them = i(form, "score_us"), i(form, "score_them")
    event.maps = s(form, "maps")
    session.add(event)

    existing = {st.member_id: st for st in
                session.exec(select(PlayerStat).where(PlayerStat.event_id == event.id)).all()}
    member_ids = {int(k.split("_")[1]) for k in form.keys() if k.startswith("played_")} | set(existing)
    for mid in member_ids:
        played = b(form, f"played_{mid}")
        st = existing.get(mid)
        if not played:
            if st:
                session.delete(st)
            continue
        st = st or PlayerStat(event_id=event.id, member_id=mid)
        st.stat1, st.stat2, st.stat3 = f(form, f"stat1_{mid}"), f(form, f"stat2_{mid}"), f(form, f"stat3_{mid}")
        st.score, st.rating = f(form, f"score_{mid}"), f(form, f"rating_{mid}")
        st.mvp = (s(form, "mvp") == str(mid))
        st.comment = s(form, f"comment_{mid}")
        session.add(st)
    session.commit()
    flash(request, "Résultat enregistré.")
    return redirect(f"/calendar/{event.id}")


def _get(session, event_id):
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(404)
    return event
