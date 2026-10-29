"""Tableau de bord."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from ..db import get_session
from ..models import HIDDEN_STATUSES, Contract, Event, Member, Team, Transaction, User
from ..security import any_user
from ..web import render

router = APIRouter()


def visible_team_ids(user: User, session: Session):
    """Un joueur ne voit que son équipe ; le staff voit tout (None = pas de filtre)."""
    if user.role != "joueur":
        return None
    member = session.get(Member, user.member_id) if user.member_id else None
    return [member.team_id] if member and member.team_id else []


@router.get("/")
def dashboard(request: Request, user: User = Depends(any_user), session: Session = Depends(get_session)):
    now = datetime.now()
    team_ids = visible_team_ids(user, session)
    teams = {t.id: t for t in session.exec(select(Team)).all()}

    upcoming_q = select(Event).where(Event.starts_at >= now - timedelta(hours=3)).order_by(Event.starts_at)
    results_q = (select(Event).where(Event.score_us.is_not(None), Event.score_them.is_not(None))
                 .order_by(Event.starts_at.desc()))
    if team_ids is not None:
        upcoming_q = upcoming_q.where(Event.team_id.in_(team_ids))
        results_q = results_q.where(Event.team_id.in_(team_ids))
    upcoming = session.exec(upcoming_q.limit(8)).all()
    results = session.exec(results_q.limit(6)).all()

    ctx = dict(upcoming=upcoming, results=results, teams=teams)
    if user.member_id:
        ctx["to_sign"] = session.exec(select(Contract).where(Contract.member_id == user.member_id,
                                                             Contract.status == "envoye")).all()

    if user.role in ("admin", "staff"):
        soon = date.today() + timedelta(days=60)
        ending = session.exec(
            select(Contract, Member).join(Member, Member.id == Contract.member_id)
            .where(Contract.end_date.is_not(None), Contract.end_date <= soon, Contract.end_date >= date.today())
            .order_by(Contract.end_date)
        ).all()
        month_start = date.today().replace(day=1)
        txs = session.exec(select(Transaction).where(Transaction.date >= month_start)).all()
        income = sum(t.amount for t in txs if t.direction == "recette")
        expense = sum(t.amount for t in txs if t.direction == "depense")
        all_txs = session.exec(select(Transaction)).all()
        balance = sum(t.amount if t.direction == "recette" else -t.amount for t in all_txs)
        members = session.exec(select(Member).where(Member.status.not_in(HIDDEN_STATUSES))).all()
        ctx.update(
            ending=ending, income=income, expense=expense, balance=balance,
            player_count=sum(1 for m in members if m.kind in ("joueur", "remplacant")),
            staff_count=sum(1 for m in members if m.kind not in ("joueur", "remplacant")),
            team_count=sum(1 for t in teams.values() if t.active),
        )
    return render(request, "dashboard.html", **ctx)
