"""Contrats : page détaillée, envoi au joueur, formulaire de signature, PDF et copie signée."""

import io
import secrets
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlmodel import Session

from .. import settings as structure_settings
from ..contract_pdf import build_contract_pdf, reference
from ..contract_template import GAME_INFO, default_clauses
from ..db import DATA_DIR, get_session
from ..models import GAMES, Contract, Member, Team, User
from ..security import admin_only, any_user, staff_only
from ..web import b, d, flash, redirect, render, s

router = APIRouter()

UPLOAD_DIR = DATA_DIR / "contracts"
ALLOWED = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_UPLOAD = 15 * 1024 * 1024
REQUIRED_FOR_SIGNING = {"last_name": "Nom", "first_name": "Prénom", "birth_date": "Date de naissance",
                        "nationality": "Nationalité", "address": "Adresse", "postal_city": "Code postal / Ville",
                        "phone": "Téléphone"}


def is_minor(member: Member) -> bool:
    if not member.birth_date:
        return False
    t = date.today()
    b = member.birth_date
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day)) < 18


def _load(session: Session, contract_id: int, user: User):
    """Renvoie (contrat, membre) si l'utilisateur a le droit de le voir."""
    contract = session.get(Contract, contract_id)
    member = session.get(Member, contract.member_id) if contract else None
    if not contract or not member:
        raise HTTPException(404)
    if user.role == "joueur" and (user.member_id != member.id or contract.status == "brouillon"):
        raise HTTPException(404)
    return contract, member


def _missing(member: Member):
    missing = [label for field, label in REQUIRED_FOR_SIGNING.items() if not getattr(member, field)]
    if is_minor(member):
        missing += [label for field, label in (("guardian_name", "Nom du représentant légal"),
                                               ("guardian_relation", "Lien de parenté")) if not getattr(member, field)]
    return missing


@router.get("/contracts/{contract_id}")
def contract_page(contract_id: int, request: Request, user: User = Depends(any_user),
                  session: Session = Depends(get_session)):
    contract, member = _load(session, contract_id, user)
    team = session.get(Team, member.team_id) if member.team_id else None
    info = structure_settings.load(session)
    game = team.game if team else "cs2"
    missing_org = [label for key, label, _ in structure_settings.FIELDS
                   if key in ("legal_name", "street", "postal_city", "representative") and not info.get(key)]
    if not structure_settings.signatories(info):
        missing_org.append("Signataires")
    return render(request, "contracts/detail.html", contract=contract, member=member, team=team,
                  custom_clauses=bool(contract.clauses), missing=_missing(member), missing_org=missing_org,
                  is_owner=user.member_id == member.id, minor=is_minor(member), ref=reference(contract, member, team, info),
                  default_platform=GAME_INFO.get(game, {}).get("plateforme", ""))


@router.get("/contracts/{contract_id}/pdf")
def contract_pdf(contract_id: int, request: Request, user: User = Depends(any_user),
                 session: Session = Depends(get_session)):
    contract, member = _load(session, contract_id, user)
    team = session.get(Team, member.team_id) if member.team_id else None
    info = structure_settings.load(session)
    pdf = build_contract_pdf(contract, member, team, info)
    suffix = {"signe": "-signe", "brouillon": "-brouillon"}.get(contract.status, "")
    name = f"Contrat_{reference(contract, member, team, info)}{suffix}.pdf"
    disposition = "inline" if request.query_params.get("view") else "attachment"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'{disposition}; filename="{name}"'})


@router.post("/contracts/{contract_id}/send")
def send_contract(contract_id: int, request: Request, user: User = Depends(staff_only),
                  session: Session = Depends(get_session)):
    contract, member = _load(session, contract_id, user)
    if contract.status == "brouillon":
        contract.status = "envoye"
        session.add(contract)
        session.commit()
        flash(request, f"Contrat envoyé : {member.nickname} peut le compléter et le signer depuis son espace.")
    return redirect(f"/contracts/{contract.id}")


@router.post("/contracts/{contract_id}/draft")
def back_to_draft(contract_id: int, request: Request, user: User = Depends(staff_only),
                  session: Session = Depends(get_session)):
    contract, _ = _load(session, contract_id, user)
    contract.status = "brouillon"
    contract.signed_name = contract.signed_at = contract.signed_ip = None
    session.add(contract)
    session.commit()
    flash(request, "Contrat repassé en brouillon (signature annulée).")
    return redirect(f"/contracts/{contract.id}")


@router.post("/contracts/{contract_id}/sign")
async def sign_contract(contract_id: int, request: Request, user: User = Depends(any_user),
                        session: Session = Depends(get_session)):
    contract, member = _load(session, contract_id, user)
    if user.member_id != member.id or contract.status != "envoye":
        raise HTTPException(403)
    form = await request.form()
    # Mise à jour des infos personnelles
    member.first_name, member.last_name = s(form, "first_name"), s(form, "last_name")
    member.birth_date, member.nationality = d(form, "birth_date"), s(form, "nationality")
    member.address, member.postal_city, member.phone = s(form, "address"), s(form, "postal_city"), s(form, "phone")
    member.platform, member.rank = s(form, "platform"), s(form, "rank")
    member.guardian_name, member.guardian_relation = s(form, "guardian_name"), s(form, "guardian_relation")
    session.add(member)
    session.commit()

    if not b(form, "save_only"):
        errors = [f"{label} : obligatoire." for label in _missing(member)]
        expected = " ".join(x for x in (member.first_name, member.last_name) if x).lower().split()
        typed = (s(form, "signature") or "").lower().split()
        if not b(form, "accept"):
            errors.append("Coche « J'ai lu et j'accepte le contrat ».")
        if is_minor(member) and not b(form, "guardian_ok"):
            errors.append("Ton représentant légal doit confirmer qu'il a lu le contrat et t'autorise à le signer.")
        if not typed or typed != expected:
            errors.append("Recopie exactement ton prénom et ton nom pour signer.")
        if errors:
            for e in errors:
                flash(request, e, "error")
            return redirect(f"/contracts/{contract.id}#signer")
        contract.status = "signe"
        contract.signed_name = " ".join(x for x in (member.first_name, member.last_name) if x)
        contract.signed_at = datetime.now().replace(microsecond=0)
        contract.signed_ip = request.client.host if request.client else None
        session.add(contract)
        session.commit()
        flash(request, "Contrat signé ! Tu peux télécharger ton exemplaire en PDF.")
    else:
        flash(request, "Informations enregistrées.")
    return redirect(f"/contracts/{contract.id}")


# --- Copie signée jointe (scan, PDF signé…) ---------------------------------


@router.post("/contracts/{contract_id}/attachment")
async def upload_attachment(contract_id: int, request: Request, user: User = Depends(staff_only),
                            session: Session = Depends(get_session)):
    contract, _ = _load(session, contract_id, user)
    form = await request.form()
    upload = form.get("file")
    if not upload or not getattr(upload, "filename", ""):
        flash(request, "Choisis un fichier.", "error")
        return redirect(f"/contracts/{contract.id}")
    ext = Path(upload.filename).suffix.lower()
    if ext not in ALLOWED:
        flash(request, "Formats acceptés : PDF, PNG, JPG.", "error")
        return redirect(f"/contracts/{contract.id}")
    data = await upload.read()
    if len(data) > MAX_UPLOAD:
        flash(request, "Fichier trop lourd (15 Mo maximum).", "error")
        return redirect(f"/contracts/{contract.id}")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    _remove_file(contract)
    stored = f"{contract.id}-{secrets.token_hex(8)}{ext}"
    (UPLOAD_DIR / stored).write_bytes(data)
    contract.attachment, contract.attachment_name = stored, Path(upload.filename).name[:120]
    session.add(contract)
    session.commit()
    flash(request, "Document joint au contrat.")
    return redirect(f"/contracts/{contract.id}")


@router.get("/contracts/{contract_id}/attachment")
def download_attachment(contract_id: int, request: Request, user: User = Depends(any_user),
                        session: Session = Depends(get_session)):
    contract, _ = _load(session, contract_id, user)
    path = UPLOAD_DIR / contract.attachment if contract.attachment else None
    if not path or not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type=ALLOWED.get(path.suffix, "application/octet-stream"),
                        filename=contract.attachment_name or path.name)


@router.post("/contracts/{contract_id}/attachment/delete")
def delete_attachment(contract_id: int, request: Request, user: User = Depends(staff_only),
                      session: Session = Depends(get_session)):
    contract, _ = _load(session, contract_id, user)
    _remove_file(contract)
    contract.attachment = contract.attachment_name = None
    session.add(contract)
    session.commit()
    flash(request, "Document retiré.")
    return redirect(f"/contracts/{contract.id}")


def _remove_file(contract: Contract) -> None:
    if contract.attachment:
        (UPLOAD_DIR / contract.attachment).unlink(missing_ok=True)


# --- Infos de la structure (en-tête des contrats) ---------------------------


@router.get("/settings")
def settings_page(request: Request, user: User = Depends(admin_only), session: Session = Depends(get_session)):
    return render(request, "settings.html", info=structure_settings.load(session),
                  fields=structure_settings.FIELDS, signatories_help=structure_settings.SIGNATORIES_HELP)


@router.post("/settings")
async def settings_save(request: Request, user: User = Depends(admin_only), session: Session = Depends(get_session)):
    form = await request.form()
    values = {key: s(form, key) for key, _, _ in structure_settings.FIELDS}
    values["signatories"] = (form.get("signatories") or "").replace("\r\n", "\n").strip() or None
    for game in GAMES:
        text = (form.get(f"clauses_{game}") or "").replace("\r\n", "\n").strip()
        # Champ vidé ou identique au modèle : on garde le modèle par défaut
        values[f"clauses_{game}"] = None if not text or text == default_clauses(game).strip() else text
    structure_settings.save(session, values)

    upload = form.get("logo")
    if upload is not None and getattr(upload, "filename", ""):
        error = _save_logo(await upload.read())
        if error:
            flash(request, error, "error")
            return redirect("/settings")
    if b(form, "remove_logo"):
        structure_settings.LOGO_PATH.unlink(missing_ok=True)
    flash(request, "Infos de la structure enregistrées.")
    return redirect("/settings")


def _save_logo(data: bytes):
    """Enregistre le logo en PNG, réduit à 1000 px de large pour garder des PDF légers."""
    from PIL import Image, UnidentifiedImageError

    if len(data) > MAX_UPLOAD:
        return "Logo trop lourd (15 Mo maximum)."
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError):
        return "Format d'image non reconnu (PNG ou JPG)."
    img = img.convert("RGBA")
    img.thumbnail((1000, 1000))
    img.save(structure_settings.LOGO_PATH, "PNG", optimize=True)
    return None


@router.get("/logo.png")
def logo():
    if not structure_settings.LOGO_PATH.is_file():
        raise HTTPException(404)
    return FileResponse(structure_settings.LOGO_PATH, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=300"})
