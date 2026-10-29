"""Génération du contrat joueur en PDF, sur la trame des contrats de la structure."""

import io
import re
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (CondPageBreak, Flowable, Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from . import settings as structure_settings
from .contract_template import GAME_INFO, default_clauses, fill
from .models import GAMES, Contract, Member, Team

NAVY = colors.HexColor("#1B2A4A")
TEAL = colors.HexColor("#2E86AB")
ORANGE = colors.HexColor("#CF6A28")
GREY = colors.HexColor("#666666")
RED = colors.HexColor("#CC0000")
SHADE = colors.HexColor("#F0F4F8")
BLANK = "____________________________"
BLANK_DATE = "____ / ____ / ________"


def _d(value) -> str:
    return value.strftime("%d / %m / %Y") if value else BLANK_DATE


def _styles():
    def ps(name, **kw):
        kw.setdefault("fontName", "Helvetica")
        kw.setdefault("fontSize", 9.5)
        kw.setdefault("leading", 13.5)
        kw.setdefault("textColor", NAVY)
        return ParagraphStyle(name, **kw)
    return {
        "cover_italic": ps("ci", fontName="Helvetica-Oblique", fontSize=10, leading=17, textColor=GREY, alignment=TA_CENTER),
        "cover": ps("c", fontSize=10, leading=17, textColor=GREY, alignment=TA_CENTER),
        "caption": ps("cap", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=NAVY, alignment=TA_CENTER),
        "title": ps("t", fontName="Helvetica-Bold", fontSize=20, leading=25, alignment=TA_CENTER),
        "division": ps("dv", fontName="Helvetica-Bold", fontSize=12.5, leading=17, textColor=ORANGE, alignment=TA_CENTER),
        "org": ps("o", fontName="Helvetica-Bold", fontSize=12.5, leading=17, textColor=TEAL, alignment=TA_CENTER),
        "confidential": ps("cf", fontName="Helvetica-Bold", fontSize=9, textColor=RED, alignment=TA_CENTER),
        "preamble": ps("pr", fontName="Helvetica-Bold", fontSize=12, leading=16, alignment=TA_CENTER, spaceAfter=10),
        "part": ps("pa", fontName="Helvetica-Bold", fontSize=9.5, textColor=TEAL, spaceBefore=12, spaceAfter=6),
        "article": ps("ar", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=TEAL, spaceBefore=14),
        "body": ps("b", alignment=TA_JUSTIFY, spaceAfter=5),
        "indent": ps("in", alignment=TA_JUSTIFY, leftIndent=9 * mm, spaceAfter=4),
        "cell": ps("ce", fontSize=9, leading=12),
        "cell_b": ps("cb", fontName="Helvetica-Bold", fontSize=9, leading=12),
        "small": ps("s", fontSize=8, leading=10.5, textColor=GREY),
        "footer_org": ps("fo", fontName="Helvetica-Bold", fontSize=9, textColor=TEAL, alignment=TA_CENTER),
        "footer_addr": ps("fa", fontSize=8, textColor=GREY, alignment=TA_CENTER),
    }


def _p(text, style):
    return Paragraph(escape(text or ""), style)


class Rule(Flowable):
    """Double filet orange, comme sur la couverture du contrat."""

    def __init__(self, width, double=True):
        super().__init__()
        self.width, self.double = width, double

    def wrap(self, *args):
        return self.width, 6 if self.double else 3

    def draw(self):
        self.canv.setStrokeColor(ORANGE)
        self.canv.setLineWidth(1)
        self.canv.line(0, 4.5 if self.double else 1.5, self.width, 4.5 if self.double else 1.5)
        if self.double:
            self.canv.line(0, 1, self.width, 1)


class ArticleTitle(Flowable):
    """Titre d'article en bleu, souligné d'un filet."""

    def __init__(self, text, style, width):
        super().__init__()
        self.para, self.width = Paragraph(escape(text), style), width

    def wrap(self, aw, ah):
        _, h = self.para.wrap(self.width, ah)
        self.h = h + 5
        return self.width, self.h + self.para.style.spaceBefore

    def draw(self):
        self.para.drawOn(self.canv, 0, 5)
        self.canv.setStrokeColor(TEAL)
        self.canv.setLineWidth(0.8)
        self.canv.line(0, 1.5, self.width, 1.5)


def _logo(width_mm, max_h_mm):
    if not structure_settings.LOGO_PATH.is_file():
        return None
    reader = ImageReader(str(structure_settings.LOGO_PATH))
    iw, ih = reader.getSize()
    w = width_mm * mm
    h = w * ih / iw
    if h > max_h_mm * mm:
        h = max_h_mm * mm
        w = h * iw / ih
    return Image(str(structure_settings.LOGO_PATH), width=w, height=h)


def _table(rows, st, label_width=48 * mm):
    data = [[_p(label, st["cell_b"]), Paragraph(value, st["cell"])] for label, value in rows]
    t = Table(data, colWidths=[label_width, None])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, NAVY),
        ("BACKGROUND", (0, 0), (0, -1), SHADE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _v(value) -> str:
    return escape(value) if value else BLANK


def reference(contract: Contract, member: Member, team: Team | None, info: dict) -> str:
    tag = info.get("short_tag") or "CT"
    code = GAME_INFO.get(team.game, {}).get("code", "GEN") if team else "GEN"
    pseudo = re.sub(r"[^A-Za-z0-9_-]", "", member.nickname) or str(member.id)
    return f"{tag}-{code}-CONTRAT-{pseudo}"


def build_contract_pdf(contract: Contract, member: Member, team: Team | None, info: dict) -> bytes:
    st = _styles()
    buf = io.BytesIO()
    org = info.get("legal_name") or "La Structure"
    game = team.game if team else "cs2"
    jeu = GAMES.get(game, "") if team else "esport"
    assoc = structure_settings.is_association(info)
    ref = reference(contract, member, team, info)
    width = A4[0] - 40 * mm

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Oblique", 7.5)
        canvas.setFillColor(GREY)
        header = (info.get("group") or "") if doc.page == 1 else f"{org} — Division {jeu}"
        canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 12 * mm, header)
        canvas.restoreState()

    class NumberedCanvas(rl_canvas.Canvas):
        """Ajoute « Page X / N » en pied de page (N connu seulement à la fin)."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                self.setFont("Helvetica-Oblique", 7.5)
                self.setFillColor(GREY)
                self.drawCentredString(A4[0] / 2, 10 * mm,
                                       f"Contrat {jeu} — {org} | Page {self._pageNumber} / {total}")
                super().showPage()
            super().save()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm,
                            bottomMargin=20 * mm, title=f"Contrat {jeu} – {org} – {member.nickname}", author=org,
                            subject=ref)

    # --- Couverture ---
    story = [Spacer(1, 14 * mm)]
    logo = _logo(80, 50)
    if logo:
        story.append(logo)
    if info.get("logo_caption"):
        story += [Spacer(1, 3 * mm), _p(info["logo_caption"], st["caption"])]
    story += [Spacer(1, 12 * mm), Rule(width), Spacer(1, 9 * mm),
              _p("CONTRAT DE JOUEUR ESPORT", st["title"]), Spacer(1, 2),
              _p(f"Division {jeu}", st["division"]), _p(org, st["org"]),
              Spacer(1, 7 * mm), Rule(width), Spacer(1, 10 * mm)]
    for key in ("legal_form", "registration", "group"):
        if info.get(key):
            story.append(_p(info[key], st["cover_italic"]))
    address = ", ".join(x for x in (info.get("street"), (info.get("postal_city") or "").split(",")[0]) if x)
    if address:
        story.append(_p(address, st["cover"]))
    story += [Spacer(1, 10 * mm),
              Paragraph(f"Référence : <b><font color='#1B2A4A'>{escape(ref)}</font></b>", st["cover"]),
              Paragraph(f"Date : <b><font color='#1B2A4A'>{_d(contract.start_date)}</font></b>", st["cover"]),
              Spacer(1, 12 * mm), _p("DOCUMENT CONFIDENTIEL", st["confidential"]), PageBreak()]

    # --- Préambule et parties ---
    story += [_p("PRÉAMBULE", st["preamble"]),
              _p("Le présent contrat (ci-après le « Contrat ») est conclu entre les parties suivantes :", st["body"]),
              _p("PARTIE 1 — L'ASSOCIATION" if assoc else "PARTIE 1 — LA STRUCTURE", st["part"]),
              _table([(label, _v(value)) for label, value in [
                  ("Dénomination", org), ("Forme juridique", info.get("legal_form")),
                  ("Groupe / Réseau", info.get("group")), ("Division", jeu),
                  ("Siège social", info.get("street")), ("Code postal / Ville", info.get("postal_city")),
                  ("Représentants légaux", info.get("representative")), ("Fonction", info.get("representative_title")),
                  ("Téléphone", info.get("phone")),
              ] if value or label in ("Dénomination", "Division", "Siège social", "Représentants légaux")], st),
              _p("PARTIE 2 — LE JOUEUR / LA JOUEUSE", st["part"]),
              _table([
                  ("Nom", _v(member.last_name)), ("Prénom", _v(member.first_name)),
                  ("Date de naissance", _d(member.birth_date)), ("Nationalité", _v(member.nationality)),
                  ("Adresse", _v(member.address)), ("Code postal / Ville", _v(member.postal_city)),
                  ("E-mail", _v(member.email)), ("Téléphone", _v(member.phone)),
                  ("Pseudonyme (Gamertag)", _v(member.nickname)), ("Jeu", escape(jeu)),
                  ("Plateforme(s)", _v(member.platform or GAME_INFO.get(game, {}).get("plateforme"))),
                  ("Rang actuel", _v(member.rank)), ("Poste / Rôle", _v(member.game_role)),
              ], st),
              Spacer(1, 6),
              _p("Ci-après désigné(e) individuellement « la Partie » et collectivement « les Parties ».", st["body"]),
              _p("Les Parties ont convenu ce qui suit :", st["body"])]

    # --- Articles ---
    start = _d(contract.start_date)
    duree = (f"pour une durée déterminée, du {start} au {_d(contract.end_date)}" if contract.end_date
             else f"pour une durée indéterminée, à compter du {start}")
    text = fill(contract.clauses or info.get(f"clauses_{game}") or default_clauses(game), {
        "structure": org, "structure_court": info.get("short_name") or org, "tag": info.get("short_tag") or "",
        "jeu": jeu, "JEU": jeu.upper(), "editeur": GAME_INFO.get(game, {}).get("editeur", "son éditeur"),
        "duree": duree, "date_debut": start,
    })
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("ARTICLE"):
            story += [CondPageBreak(30 * mm), ArticleTitle(line.upper(), st["article"], width), Spacer(1, 6)]
        elif re.match(r"^([a-z]\)|•|-)\s", line):
            story.append(_p(line if not line.startswith("-") else "•" + line[1:], st["indent"]))
        else:
            m = re.match(r"^(\d+\.\d+\.)\s*(.*)$", line)
            story.append(Paragraph(f"<b>{m.group(1)}</b> {escape(m.group(2))}" if m else escape(line), st["body"]))

    if contract.notes or contract.monthly_amount:
        extra = []
        if contract.monthly_amount:
            amount = f"{contract.monthly_amount:,.2f}".replace(",", " ").replace(".", ",").replace(",00", "")
            extra.append(f"Montant mensuel convenu : {amount} €.")
        if contract.notes:
            extra.append(contract.notes)
        story += [CondPageBreak(30 * mm), ArticleTitle("CONDITIONS PARTICULIÈRES", st["article"], width), Spacer(1, 6)]
        story += [_p(x, st["body"]) for x in "\n".join(extra).split("\n") if x.strip()]

    # --- Signatures ---
    signed = contract.status == "signe" and contract.signed_at
    sign_date = _d(contract.signed_at.date()) if signed else BLANK_DATE
    place = info.get("signature_place") or f"Fait à {BLANK}"
    left = [f"<b>Pour {'l’Association' if assoc else 'la Structure'}</b>", "", escape(org), f"Division {escape(jeu)}", ""]
    sigs = structure_settings.signatories(info)
    if not sigs and info.get("representative"):
        sigs = [(f"{info['representative']} — {info.get('representative_title') or ''}".strip(" —"), "")]
    for label, sig in sigs:
        left += [escape(label), f"Signature : {escape(sig) if sig else ''}", ""]
    if signed:
        player_sig = (f"Signature : <b>signé électroniquement</b><br/>par {escape(contract.signed_name or '')}"
                      f"<br/>le {sign_date} à {contract.signed_at:%H:%M}"
                      + (f"<br/><font size=7 color='#666666'>IP : {escape(contract.signed_ip)}</font>"
                         if contract.signed_ip else ""))
    else:
        player_sig = "Signature :"
    right = ["<b>Le Joueur / La Joueuse</b>", "", f"Nom : {_v(member.last_name)}", f"Prénom : {_v(member.first_name)}",
             f"Gamertag : {escape(member.nickname)}", "", player_sig]
    sig_table = Table([[Paragraph("<br/>".join(left), st["cell"]), Paragraph("<br/>".join(right), st["cell"])]],
                      colWidths=[width / 2, width / 2])
    sig_table.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, NAVY), ("BOX", (1, 0), (1, 0), 0.6, NAVY),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    story.append(KeepTogether([
        ArticleTitle("SIGNATURES", st["article"], width), Spacer(1, 6),
        _p("Fait en deux (2) exemplaires originaux, un pour chaque Partie.", st["body"]),
        Paragraph(f"{escape(place)}, le {sign_date}", st["body"]), Spacer(1, 6), sig_table,
    ]))

    # --- Représentant légal (joueurs mineurs) ---
    full = " ".join(x for x in (member.first_name, member.last_name) if x) or BLANK
    guardian_sig = "Signature :"
    if signed and member.guardian_name:
        guardian_sig = f"Signature : <b>approuvé électroniquement</b><br/>le {sign_date}"
    g_table = Table([[Paragraph(f"Nom : {_v(member.guardian_name)}<br/><br/>Lien de parenté : "
                                f"{_v(member.guardian_relation)}", st["cell"]),
                      Paragraph(guardian_sig, st["cell"])]], colWidths=[width / 2, width / 2])
    g_table.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, NAVY), ("BOX", (1, 0), (1, 0), 0.6, NAVY),
                                 ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 8),
                                 ("BOTTOMPADDING", (0, 0), (-1, -1), 18), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    story.append(KeepTogether([
        ArticleTitle("JOUEURS MINEURS — SIGNATURE DU REPRÉSENTANT LÉGAL", st["article"], width), Spacer(1, 6),
        Paragraph(f"Je soussigné(e), {_v(member.guardian_name)}, en qualité de représentant légal de "
                  f"{escape(full)}, autorise mon enfant à signer le présent Contrat.", st["body"]),
        Spacer(1, 4), g_table,
    ]))

    # --- Pied de document ---
    closing = [Spacer(1, 10 * mm), Rule(width, double=False), Spacer(1, 6 * mm)]
    small_logo = _logo(26, 16)
    if small_logo:
        closing += [small_logo, Spacer(1, 2 * mm)]
    closing.append(_p(" — ".join(x for x in (org, info.get("group")) if x), st["footer_org"]))
    contact = " | ".join(x for x in (", ".join(y for y in (info.get("street"), info.get("postal_city")) if y),
                                      f"Tél. : {info['phone']}" if info.get("phone") else "") if x)
    if contact:
        closing.append(_p(contact, st["footer_addr"]))
    closing += [Spacer(1, 4 * mm),
                _p(f"Document généré le {date.today():%d/%m/%Y}." + (
                    f" Signature électronique simple : le Joueur a validé le contrat en ligne depuis son espace "
                    f"personnel." if signed else ""), st["small"])]
    story.append(KeepTogether(closing))

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate, canvasmaker=NumberedCanvas)
    return buf.getvalue()
