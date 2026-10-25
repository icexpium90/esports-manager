"""Finances : recettes, dépenses, bilan et sponsors."""

import csv
import io
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from ..db import get_session
from ..models import SPONSOR_STATUS, TRANSACTION_CATEGORIES, Sponsor, Team, Transaction, User
from ..security import staff_only
from ..web import d, f, flash, i, redirect, render, s

router = APIRouter(prefix="/finances")


def _signed(t):
    return t.amount if t.direction == "recette" else -t.amount


@router.get("")
def overview(request: Request, year: int | None = None, team: int | None = None,
             user: User = Depends(staff_only), session: Session = Depends(get_session)):
    year = year or date.today().year
    q = (select(Transaction).where(Transaction.date >= date(year, 1, 1), Transaction.date <= date(year, 12, 31))
         .order_by(Transaction.date.desc(), Transaction.id.desc()))
    if team:
        q = q.where(Transaction.team_id == team)
    txs = session.exec(q).all()

    months = [{"income": 0.0, "expense": 0.0} for _ in range(12)]
    by_cat = {"recette": defaultdict(float), "depense": defaultdict(float)}
    for t in txs:
        key = "income" if t.direction == "recette" else "expense"
        months[t.date.month - 1][key] += t.amount
        by_cat[t.direction][t.category] += t.amount
    income = sum(m["income"] for m in months)
    expense = sum(m["expense"] for m in months)
    all_balance = sum(_signed(t) for t in session.exec(select(Transaction)).all())
    peak = max([max(m["income"], m["expense"]) for m in months] + [1])

    years = sorted({t.date.year for t in session.exec(select(Transaction)).all()} | {date.today().year},
                   reverse=True)
    teams = {t.id: t for t in session.exec(select(Team)).all()}
    sponsors = {sp.id: sp for sp in session.exec(select(Sponsor)).all()}
    return render(request, "finances/index.html", txs=txs, months=months, peak=peak, income=income,
                  expense=expense, balance=all_balance, by_cat=by_cat, year=year, years=years, teams=teams,
                  sponsors=sponsors, team=team)


@router.get("/export.csv")
def export_csv(year: int | None = None, user: User = Depends(staff_only), session: Session = Depends(get_session)):
    year = year or date.today().year
    txs = session.exec(select(Transaction).where(Transaction.date >= date(year, 1, 1),
                                                 Transaction.date <= date(year, 12, 31))
                       .order_by(Transaction.date)).all()
    teams = {t.id: t.name for t in session.exec(select(Team)).all()}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Date", "Type", "Catégorie", "Libellé", "Montant", "Équipe", "Notes"])
    for t in txs:
        cat = TRANSACTION_CATEGORIES.get(t.direction, {}).get(t.category, t.category)
        w.writerow([t.date.isoformat(), "Recette" if t.direction == "recette" else "Dépense", cat, t.label,
                    f"{_signed(t):.2f}".replace(".", ","), teams.get(t.team_id, ""), t.notes or ""])
    data = "﻿" + buf.getvalue()  # BOM pour qu'Excel lise bien les accents
    return StreamingResponse(iter([data]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="finances-{year}.csv"'})


# --- Transactions -----------------------------------------------------------


def _form_ctx(session):
    return dict(teams=session.exec(select(Team).order_by(Team.name)).all(),
                sponsors=session.exec(select(Sponsor).order_by(Sponsor.name)).all())


@router.get("/new")
def new_tx(request: Request, direction: str = "depense", user: User = Depends(staff_only),
           session: Session = Depends(get_session)):
    item = Transaction(date=date.today(), direction=direction if direction in TRANSACTION_CATEGORIES else "depense",
                       amount=0, label="")
    return render(request, "finances/form.html", item=item, is_new=True, **_form_ctx(session))


@router.get("/{tx_id}/edit")
def edit_tx(tx_id: int, request: Request, user: User = Depends(staff_only), session: Session = Depends(get_session)):
    return render(request, "finances/form.html", item=_get(session, Transaction, tx_id), is_new=False,
                  **_form_ctx(session))


@router.post("/new")
@router.post("/{tx_id}/edit")
async def save_tx(request: Request, tx_id: int | None = None, user: User = Depends(staff_only),
                  session: Session = Depends(get_session)):
    form = await request.form()
    item = _get(session, Transaction, tx_id) if tx_id else Transaction(date=date.today(), amount=0, label="")
    item.direction = s(form, "direction") if s(form, "direction") in TRANSACTION_CATEGORIES else "depense"
    cat = s(form, "category")
    item.category = cat if cat in TRANSACTION_CATEGORIES[item.direction] else "autre"
    item.date = d(form, "date") or date.today()
    item.amount = abs(f(form, "amount") or 0)
    item.label = s(form, "label") or "Sans libellé"
    item.team_id, item.sponsor_id = i(form, "team_id"), i(form, "sponsor_id")
    item.notes = s(form, "notes")
    session.add(item)
    session.commit()
    flash(request, "Opération enregistrée.")
    return redirect(f"/finances?year={item.date.year}")


@router.post("/{tx_id}/delete")
def delete_tx(tx_id: int, request: Request, user: User = Depends(staff_only), session: Session = Depends(get_session)):
    item = _get(session, Transaction, tx_id)
    session.delete(item)
    session.commit()
    flash(request, "Opération supprimée.")
    return redirect("/finances")


# --- Sponsors ---------------------------------------------------------------


@router.get("/sponsors")
def sponsors(request: Request, user: User = Depends(staff_only), session: Session = Depends(get_session)):
    items = session.exec(select(Sponsor).order_by(Sponsor.status, Sponsor.name)).all()
    received = defaultdict(float)
    for t in session.exec(select(Transaction).where(Transaction.sponsor_id.is_not(None))).all():
        received[t.sponsor_id] += _signed(t)
    active_total = sum(sp.yearly_amount for sp in items if sp.status == "actif")
    return render(request, "finances/sponsors.html", items=items, received=received, active_total=active_total)


@router.get("/sponsors/new")
def new_sponsor(request: Request, user: User = Depends(staff_only)):
    return render(request, "finances/sponsor_form.html", item=Sponsor(name=""), is_new=True)


@router.get("/sponsors/{sponsor_id}/edit")
def edit_sponsor(sponsor_id: int, request: Request, user: User = Depends(staff_only),
                 session: Session = Depends(get_session)):
    return render(request, "finances/sponsor_form.html", item=_get(session, Sponsor, sponsor_id), is_new=False)


@router.post("/sponsors/new")
@router.post("/sponsors/{sponsor_id}/edit")
async def save_sponsor(request: Request, sponsor_id: int | None = None, user: User = Depends(staff_only),
                       session: Session = Depends(get_session)):
    form = await request.form()
    item = _get(session, Sponsor, sponsor_id) if sponsor_id else Sponsor(name="")
    item.name = s(form, "name") or "Sans nom"
    item.status = s(form, "status") if s(form, "status") in SPONSOR_STATUS else "prospect"
    item.contact_name, item.contact_email = s(form, "contact_name"), s(form, "contact_email")
    item.yearly_amount = f(form, "yearly_amount") or 0
    item.start_date, item.end_date = d(form, "start_date"), d(form, "end_date")
    item.deliverables, item.notes = s(form, "deliverables"), s(form, "notes")
    session.add(item)
    session.commit()
    flash(request, "Sponsor enregistré.")
    return redirect("/finances/sponsors")


def _get(session, model, item_id):
    item = session.get(model, item_id)
    if not item:
        raise HTTPException(404)
    return item
