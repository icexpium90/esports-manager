"""Infos de la structure (en-tête, parties et signatures des contrats) et logo."""

import os

from sqlmodel import Session, select

from .contract_template import default_clauses
from .db import DATA_DIR
from .models import GAMES, Setting

# (clé, libellé, aide / exemple)
FIELDS = [
    ("legal_name", "Dénomination", "ex. LUSOSTATIS ESPORT"),
    ("short_name", "Nom court", "repris dans « porter le tag … ou … » ; par défaut le 1er mot de la dénomination"),
    ("short_tag", "Tag", "ex. LSG — sert aussi aux références de contrat"),
    ("legal_form", "Forme juridique", "ex. Association sans but lucratif (ASBL)"),
    ("registration", "Enregistrement", "ex. Enregistrée au Grand-Duché de Luxembourg"),
    ("group", "Groupe / réseau", "ex. BENELUX BUSINESS AREA"),
    ("street", "Siège social", "ex. 25 Rue Henri Koch"),
    ("postal_city", "Code postal / Ville", "ex. L-4354 Esch-sur-Alzette, Luxembourg"),
    ("phone", "Téléphone", ""),
    ("representative", "Représentants légaux", "ex. M. Dupont et Mme Martin"),
    ("representative_title", "Fonction", "ex. Co-Présidents"),
    ("signature_place", "Lieu de signature", "ex. En hybride à Esch-sur-Alzette"),
    ("logo_caption", "Texte sous le logo", "ex. MAIN HOLDING HOUSE at ESCH S/ ALZETTE"),
]
SIGNATORIES_HELP = "Un par ligne : « Nom — Fonction | NOM EN SIGNATURE » (la partie après | est facultative)"

LOGO_PATH = DATA_DIR / "logo.png"


def load(session: Session) -> dict:
    data = {"legal_name": os.environ.get("STRUCTURE_NAME", "Ma structure"), "legal_form": "Association"}
    data.update({s.key: s.value for s in session.exec(select(Setting)).all() if s.value})
    data.setdefault("short_name", (data["legal_name"].split() or [""])[0])
    for game in GAMES:
        data.setdefault(f"clauses_{game}", default_clauses(game))
    data["has_logo"] = LOGO_PATH.is_file()
    return data


def save(session: Session, values: dict) -> None:
    for key, value in values.items():
        row = session.get(Setting, key) or Setting(key=key)
        row.value = value
        session.add(row)
    session.commit()


def signatories(info: dict):
    """Liste de (nom — fonction, nom en signature)."""
    rows = []
    for line in (info.get("signatories") or "").splitlines():
        if line.strip():
            label, _, sig = line.partition("|")
            rows.append((label.strip(), sig.strip()))
    return rows


def is_association(info: dict) -> bool:
    form = (info.get("legal_form") or "").lower()
    return "association" in form or "asbl" in form or "loi 1901" in form
