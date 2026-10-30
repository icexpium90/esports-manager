"""Génération du contrat joueur en PDF (charte LUSOSTATIS : couverture sombre, bandeaux violets)."""

import io
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

from . import settings as structure_settings
from .contract_template import GAME_INFO, default_clauses, fill
from .models import GAMES, Contract, Member, Team

# --- Charte -----------------------------------------------------------------
PURPLE = colors.HexColor("#7B2CBF")
DEEP = colors.HexColor("#3C096C")
ORANGE = colors.HexColor("#FF8A1F")
INK = colors.HexColor("#1F1A26")
MUTED = colors.HexColor("#7D7488")
LAVENDER = colors.HexColor("#F6F1FB")
LINE = colors.HexColor("#E6DCEF")
BLANK_C = "#CFC5DB"
NIGHT = colors.HexColor("#120A1C")
CARD = colors.HexColor("#1F1330")
CARD_LINE = colors.HexColor("#3A2452")
COVER_TEXT = colors.HexColor("#B4ADBD")

PAGE_W, PAGE_H = A4
MARGIN_X = 62
CONTENT_W = PAGE_W - 2 * MARGIN_X
BLANK = f"<font color='{BLANK_C}'>" + "_ " * 22 + "</font>"
BLANK_SHORT = f"<font color='{BLANK_C}'>" + "_ " * 13 + "</font>"
BLANK_DATE = f"<font color='{BLANK_C}'>_ _ _ _ / _ _ _ _ / _ _ _ _ _ _ _ _</font>"

FONT_DIR = Path(__file__).parent / "fonts"
_FONTS = {"Pop": "Poppins-Regular", "Pop-M": "Poppins-Medium", "Pop-SB": "Poppins-SemiBold", "Pop-B": "Poppins-Bold"}


def _register_fonts():
    if "Pop" in pdfmetrics.getRegisteredFontNames():
        return
    for name, file in _FONTS.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / f"{file}.ttf")))
    pdfmetrics.registerFontFamily("Pop", normal="Pop", bold="Pop-B", italic="Pop", boldItalic="Pop-B")


def _styles():
    def ps(name, **kw):
        kw.setdefault("fontName", "Pop")
        kw.setdefault("fontSize", 8.2)
        kw.setdefault("leading", 13)
        kw.setdefault("textColor", INK)
        return ParagraphStyle(name, **kw)
    return {
        "body": ps("body", alignment=TA_JUSTIFY),
        "intro": ps("intro", leftIndent=32, spaceAfter=4),
        "num": ps("num", fontName="Pop-SB", textColor=PURPLE),
        "marker": ps("marker", fontName="Pop-SB", textColor=ORANGE),
        "subhead": ps("subhead", fontName="Pop-B"),
        "part": ps("part", fontName="Pop-B", fontSize=8.6, textColor=DEEP),
        "label": ps("label", fontSize=6.9, leading=10, textColor=MUTED),
        "value": ps("value", fontName="Pop-M", fontSize=7.6, leading=10.5),
        "card_title": ps("ct", fontName="Pop-B", fontSize=9, leading=12, textColor=DEEP),
        "card_sub": ps("cs", fontSize=6.6, leading=9, textColor=MUTED),
        "card_text": ps("ctx", fontSize=7.6, leading=11),
        "sig_label": ps("sl", fontSize=6.6, leading=9, textColor=MUTED),
        "sig_done": ps("sd", fontSize=7.4, leading=10.5, textColor=DEEP),
    }


def _p(text, style):
    return Paragraph(escape(text or ""), style)


def _d(value) -> str:
    return value.strftime("%d / %m / %Y") if value else BLANK_DATE


def _v(value, blank=BLANK) -> str:
    return escape(value) if value else blank


# --- Éléments graphiques ----------------------------------------------------


class SectionBar(Flowable):
    """Bandeau violet arrondi : numéro orange + titre blanc."""

    def __init__(self, number, title, width=CONTENT_W):
        super().__init__()
        self.number, self.title, self.width, self.height = number, title, width, 22

    def wrap(self, *args):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(PURPLE)
        c.roundRect(0, 0, self.width, self.height, 11, stroke=0, fill=1)
        c.setFont("Pop-B", 9.2)
        c.setFillColor(ORANGE)
        c.drawString(15, 7.4, self.number)
        c.setFillColor(colors.white)
        c.drawString(40, 7.4, self.title)


def _chevron(c, apex_x, cy, w, h, t, direction, color):
    """Chevron épais : direction=1 → « < » (bras vers la droite), -1 → « > »."""
    c.setStrokeColor(color)
    c.setLineWidth(t)
    c.setLineJoin(0)
    c.setLineCap(0)
    path = c.beginPath()
    path.moveTo(apex_x + direction * w, cy + h / 2)
    path.lineTo(apex_x, cy)
    path.lineTo(apex_x + direction * w, cy - h / 2)
    c.drawPath(path, stroke=1, fill=0)


def _chevrons(c, scale=1.0):
    _chevron(c, 4 * scale, 104 * scale, 30 * scale, 52 * scale, 12 * scale, 1, ORANGE)
    _chevron(c, 36 * scale, 38 * scale, 32 * scale, 68 * scale, 12 * scale, -1, PURPLE)
    _chevron(c, 46 * scale, 38 * scale, 32 * scale, 68 * scale, 12 * scale, 1, ORANGE)


def _crosses(c, x, y, size=9, gap=6):
    c.setStrokeColor(ORANGE)
    c.setLineWidth(2)
    c.setLineCap(0)
    for i in range(3):
        x0 = x + i * (size + gap)
        c.line(x0, y, x0 + size, y + size)
        c.line(x0, y + size, x0 + size, y)


def _logo_paths():
    """Logo d'origine + version « filigrane » (violet sombre) pour la couverture, mise en cache."""
    src = structure_settings.LOGO_PATH
    if not src.is_file():
        return None, None
    faded = src.with_name("logo_cover.png")
    if not faded.is_file() or faded.stat().st_mtime < src.stat().st_mtime:
        from PIL import Image
        img = Image.open(src).convert("RGBA")
        lo, hi = (0x2A, 0x13, 0x40), (0x5E, 0x40, 0x82)
        px = img.load()
        for yy in range(img.height):
            for xx in range(img.width):
                r, g, b, a = px[xx, yy]
                if a:
                    t = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                    px[xx, yy] = tuple(int(lo[i] + (hi[i] - lo[i]) * t) for i in range(3)) + (int(a * 0.92),)
        img.save(faded, "PNG", optimize=True)
    return src, faded


def _draw_image(c, path, cx, cy, max_w, max_h):
    reader = ImageReader(str(path))
    iw, ih = reader.getSize()
    k = min(max_w / iw, max_h / ih)
    w, h = iw * k, ih * k
    c.drawImage(reader, cx - w / 2, cy - h / 2, w, h, mask="auto")
    return h


def _strip_registration(text: str) -> str:
    return re.sub(r"^enregistr\w*\s+(au|aux|à|en|dans)\s+", "", text or "", flags=re.I).strip()


# --- Construction -----------------------------------------------------------


def reference(contract: Contract, member: Member, team: Team | None, info: dict) -> str:
    tag = info.get("short_tag") or "CT"
    code = GAME_INFO.get(team.game, {}).get("code", "GEN") if team else "GEN"
    pseudo = re.sub(r"[^A-Za-z0-9_-]", "", member.nickname) or str(member.id)
    return f"{tag}-{code}-CONTRAT-{pseudo}"


def _numbered(num, html, st, kind="num"):
    """Paragraphe numéroté (1.1.) ou sous-point (a), •) aligné comme sur le modèle."""
    if kind == "num":
        cols = [32, 30, CONTENT_W - 62]
        row = ["", Paragraph(num, st["num"]), Paragraph(html, st["body"])]
    else:
        cols = [62, 16, CONTENT_W - 78]
        row = ["", Paragraph(num, st["marker"]), Paragraph(html, st["body"])]
    t = Table([row], colWidths=cols)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5 if kind == "num" else 2.5)]))
    return t


def _party_card(title, rows, st):
    data = [[Paragraph(escape(title), st["part"]), ""]]
    data += [[Paragraph(escape(label), st["label"]), Paragraph(value, st["value"])] for label, value in rows]
    t = Table(data, colWidths=[124, CONTENT_W - 124])
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), LAVENDER),
        ("SPAN", (0, 0), (1, 0)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 15), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("TOPPADDING", (0, 0), (-1, 0), 10), ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
        ("LINEBEFORE", (0, 0), (0, -1), 2.4, PURPLE),
    ]
    for r in range(1, len(data) - 1):
        style.append(("LINEBELOW", (0, r), (-1, r), 0.5, LINE))
    t.setStyle(TableStyle(style))
    return t


def _box(height, content=None, width=None):
    t = Table([[content or ""]], colWidths=[width], rowHeights=[height])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    return t


def _card(cells, top_color, width):
    t = Table([[cells]], colWidths=[width])
    style = [("BACKGROUND", (0, 0), (-1, -1), LAVENDER), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 13), ("RIGHTPADDING", (0, 0), (-1, -1), 13),
             ("TOPPADDING", (0, 0), (-1, -1), 11), ("BOTTOMPADDING", (0, 0), (-1, -1), 13)]
    if top_color:
        style.append(("LINEABOVE", (0, 0), (-1, 0), 2, top_color))
    t.setStyle(TableStyle(style))
    return t


def _side_by_side(left, right):
    gap = 14
    w = (CONTENT_W - gap) / 2
    t = Table([[left, "", right]], colWidths=[w, gap, w])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t, w


def build_contract_pdf(contract: Contract, member: Member, team: Team | None, info: dict) -> bytes:
    _register_fonts()
    st = _styles()
    buf = io.BytesIO()
    org = info.get("legal_name") or "La Structure"
    game = team.game if team else "cs2"
    jeu = GAMES.get(game, "esport") if team else "esport"
    assoc = structure_settings.is_association(info)
    ref = reference(contract, member, team, info)
    logo, logo_cover = _logo_paths()
    city = (info.get("postal_city") or "").split(",")[0].strip()
    address_line = ", ".join(x for x in (info.get("street"), city) if x)
    # Paraphe électronique : initiales du joueur une fois le contrat signé en ligne
    paraphe = ""
    if contract.status == "signe" and contract.signed_at:
        words = (contract.signed_name or "").replace("-", " ").split()
        paraphe = ".".join(w[0].upper() for w in words if w) + "." if words else ""

    # --- Fonds de page ---
    def cover(c, doc):
        c.saveState()
        c.setFillColor(NIGHT)
        c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
        cx, cy = PAGE_W / 2, PAGE_H - 282
        for radius, color in ((300, "#170B24"), (255, "#1C0C2B"), (210, "#210D33"), (165, "#270F3C"), (120, "#2D1146")):
            c.setFillColor(colors.HexColor(color))
            c.circle(cx, cy, radius, stroke=0, fill=1)
        if logo_cover:
            h = _draw_image(c, logo_cover, cx, cy, 300, 175)
            if info.get("logo_caption"):
                c.setFont("Pop-M", 6.8)
                c.setFillColor(colors.HexColor("#6E6080"))
                c.drawCentredString(cx, cy - h / 2 - 12, info["logo_caption"].upper())
        c.setFillColor(ORANGE)
        c.setFont("Pop-M", 8)
        label = f"DIVISION {jeu.upper()}"
        c.drawCentredString(cx, 422, label.replace(" ", "  "), charSpace=0.9)
        c.setFillColor(colors.white)
        c.setFont("Pop-B", 25)
        c.drawCentredString(cx, 390, "Contrat de joueur esport")
        sub = " · ".join(x for x in (info.get("legal_form"), _strip_registration(info.get("registration"))) if x)
        c.setFillColor(COVER_TEXT)
        c.setFont("Pop", 8.6)
        c.drawCentredString(cx, 368, sub)
        # Cartes Référence / Date / Joueur
        w, gap, h, top = 143, 13, 43, 356
        x0 = cx - (3 * w + 2 * gap) / 2
        for i, (lab, val) in enumerate((("RÉFÉRENCE", ref), ("DATE", contract.start_date.strftime("%d / %m / %Y")),
                                         ("JOUEUR", member.nickname))):
            x = x0 + i * (w + gap)
            c.setFillColor(CARD)
            c.setStrokeColor(CARD_LINE)
            c.setLineWidth(0.6)
            c.roundRect(x, top - h, w, h, 6, stroke=1, fill=1)
            c.setFillColor(ORANGE)
            c.setFont("Pop-SB", 5.6)
            c.drawCentredString(x + w / 2, top - 13, lab)
            c.setFillColor(colors.white)
            size = 8.6
            while pdfmetrics.stringWidth(val, "Pop-M", size) > w - 10 and size > 5.5:
                size -= 0.3
            c.setFont("Pop-M", size)
            c.drawCentredString(x + w / 2, top - 30, val)
        c.setFillColor(PURPLE)
        c.roundRect(cx - 75, 268, 150, 21, 10.5, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Pop-B", 7)
        c.drawCentredString(cx, 275.6, "DOCUMENT CONFIDENTIEL")
        _chevrons(c, 1.45)
        _crosses(c, 453, 56, 10, 6)
        c.setFillColor(colors.HexColor("#9A93A6"))
        c.setFont("Pop", 6.4)
        c.drawCentredString(cx, 33, " · ".join(x for x in (info.get("group"), address_line) if x))
        c.restoreState()

    def page(c, doc):
        c.saveState()
        c.setFont("Pop-B", 7.4)
        c.setFillColor(INK)
        c.drawString(MARGIN_X, PAGE_H - 44, org)
        x = MARGIN_X + pdfmetrics.stringWidth(org, "Pop-B", 7.4)
        c.setFont("Pop", 7.4)
        c.setFillColor(MUTED)
        c.drawString(x + 4, PAGE_H - 44, f"|  Contrat de joueur — {jeu}")
        if logo:
            _draw_image(c, logo, PAGE_W - MARGIN_X - 28, PAGE_H - 41, 60, 42)
        _chevrons(c, 1.0)
        _crosses(c, 452, 51, 9, 5.5)
        c.setFont("Pop", 6.2)
        c.setFillColor(colors.HexColor("#9A93A6"))
        left = f"Réf. {ref}  ·  Document confidentiel  ·  Paraphe : "
        para = paraphe or "______"
        width = pdfmetrics.stringWidth(left, "Pop", 6.2) + pdfmetrics.stringWidth(para, "Pop-B", 7)
        x = PAGE_W / 2 - width / 2
        c.drawString(x, 30, left)
        c.setFont("Pop-B", 7)
        c.setFillColor(PURPLE if paraphe else colors.HexColor("#9A93A6"))
        c.drawString(x + pdfmetrics.stringWidth(left, "Pop", 6.2), 30, para)
        c.setFont("Pop-M", 8.5)
        c.setFillColor(INK)
        c.drawRightString(PAGE_W - 48, 30, str(doc.page))
        c.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4, title=f"Contrat {jeu} – {org} – {member.nickname}", author=org,
                          subject=ref)
    doc.addPageTemplates([
        PageTemplate("cover", [Frame(MARGIN_X, 100, CONTENT_W, 100, id="c")], onPage=cover),
        PageTemplate("body", [Frame(MARGIN_X, 92, CONTENT_W, PAGE_H - 92 - 76, id="b",
                                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=page),
    ])

    story = [NextPageTemplate("body"), PageBreak()]

    # --- Préambule et parties ---
    story += [SectionBar("00", "Préambule"), Spacer(1, 8),
              _p("Le présent contrat (ci-après le « Contrat ») est conclu entre les parties suivantes :", st["intro"]),
              Spacer(1, 10)]
    org_rows = [(label, value) for label, value in [
        ("Dénomination", org), ("Forme juridique", info.get("legal_form")), ("Groupe / Réseau", info.get("group")),
        ("Division", jeu), ("Siège social", info.get("street")), ("Code postal / Ville", info.get("postal_city")),
        ("Représentants légaux", info.get("representative")), ("Fonction", info.get("representative_title")),
        ("Téléphone", info.get("phone")),
    ] if value or label in ("Siège social", "Représentants légaux")]
    story.append(_party_card("Partie 1 — L'Association" if assoc else "Partie 1 — La Structure",
                             [(label, _v(value)) for label, value in org_rows], st))
    story.append(Spacer(1, 14))
    story.append(_party_card("Partie 2 — Le Joueur / La Joueuse", [
        ("Nom", _v(member.last_name)), ("Prénom", _v(member.first_name)),
        ("Date de naissance", _d(member.birth_date)), ("Nationalité", _v(member.nationality)),
        ("Adresse", _v(member.address)), ("Code postal / Ville", _v(member.postal_city)),
        ("E-mail", _v(member.email)), ("Téléphone", _v(member.phone)),
        ("Pseudonyme (Gamertag)", _v(member.nickname)), ("Jeu", escape(jeu)),
        ("Plateforme(s)", _v(member.platform or GAME_INFO.get(game, {}).get("plateforme"))),
        ("Rang actuel", _v(member.rank)), ("Poste / Rôle", _v(member.game_role)),
    ], st))
    story += [Spacer(1, 12),
              _p("Ci-après désigné(e) individuellement « la Partie » et collectivement « les Parties ». "
                 "Les Parties ont convenu ce qui suit :", ParagraphStyle("pi", parent=st["intro"], alignment=TA_JUSTIFY)),
              PageBreak()]

    # --- Articles ---
    start = contract.start_date.strftime("%d / %m / %Y")
    duree = (f"pour une durée déterminée, du {start} au {contract.end_date.strftime('%d / %m / %Y')}"
             if contract.end_date else f"pour une durée indéterminée, à compter du {start}")
    text = fill(contract.clauses or info.get(f"clauses_{game}") or default_clauses(game), {
        "structure": org, "structure_court": info.get("short_name") or org, "tag": info.get("short_tag") or "",
        "jeu": jeu, "JEU": jeu.upper(), "editeur": GAME_INFO.get(game, {}).get("editeur", "son éditeur"),
        "duree": duree, "date_debut": start,
    })
    last_article = 0
    first = True
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        art = re.match(r"^ARTICLE\s+(\d+)\s*[—–-]\s*(.+)$", line, re.I)
        if art:
            last_article = int(art.group(1))
            story += [CondPageBreak(90)] + ([] if first else [Spacer(1, 12)])
            story += [SectionBar(f"{last_article:02d}", art.group(2)), Spacer(1, 9)]
            first = False
            continue
        marker = re.match(r"^([a-z]\)|•|-)\s+(.*)$", line)
        if marker:
            sym = "•" if marker.group(1) in ("•", "-") else marker.group(1)
            story.append(_numbered(sym, escape(marker.group(2)), st, kind="sub"))
            continue
        num = re.match(r"^(\d+\.\d+\.)\s*(.*)$", line)
        if num:
            body = num.group(2)
            if len(body) < 70 and not body.rstrip().endswith((".", ":", ";")) and " — " not in body[:3]:
                html = f"<font name='Pop-B'>{escape(body)}</font>"
            else:
                lead = re.match(r"^(.{3,60}?) — (.*)$", body)
                html = (f"<font name='Pop-B'>{escape(lead.group(1))}</font> — {escape(lead.group(2))}"
                        if lead else escape(body))
            story.append(_numbered(num.group(1), html, st))
        else:
            story.append(Paragraph(escape(line), ParagraphStyle("free", parent=st["body"], leftIndent=32,
                                                                spaceAfter=4)))

    next_no = last_article + 1
    if contract.notes or contract.monthly_amount:
        lines = []
        if contract.monthly_amount:
            amount = f"{contract.monthly_amount:,.2f}".replace(",", " ").replace(".", ",").replace(",00", "")
            lines.append(f"Montant mensuel convenu : {amount} €.")
        lines += [x for x in (contract.notes or "").split("\n") if x.strip()]
        story += [CondPageBreak(90), Spacer(1, 12), SectionBar(f"{next_no:02d}", "Conditions particulières"),
                  Spacer(1, 9)]
        story += [_numbered(f"{next_no}.{i}.", escape(x), st) for i, x in enumerate(lines, 1)]
        next_no += 1

    # --- Signatures ---
    signed = contract.status == "signe" and contract.signed_at
    sign_date = contract.signed_at.strftime("%d / %m / %Y") if signed else BLANK_DATE
    place = escape(info.get("signature_place") or "Fait à") + ","
    sigs = structure_settings.signatories(info)
    if not sigs and info.get("representative"):
        sigs = [(f"{info['representative']} — {info.get('representative_title') or ''}".strip(" —"), "")]
    _, half = _side_by_side("", "")
    inner = half - 26

    left = [Paragraph(f"Pour {'l’Association' if assoc else 'la Structure'}", st["card_title"]),
            Paragraph(f"{escape(org)} — Division {escape(jeu)}", st["card_sub"]), Spacer(1, 8)]
    for label, sig in sigs:
        name, _, role = label.partition("—")
        left += [Paragraph(f"<font name='Pop-B'>{escape(name.strip())}</font>"
                           + (f" — {escape(role.strip())}" if role else ""), st["card_text"]),
                 Paragraph("Signature :", st["sig_label"]), Spacer(1, 2),
                 _box(46, Paragraph(escape(sig), st["sig_done"]) if sig else None, inner), Spacer(1, 8)]
    if signed:
        sig_content = Paragraph(
            f"<font name='Pop-B'>Lu et approuvé — signé électroniquement</font><br/>par "
            f"{escape(contract.signed_name or '')}<br/>le {sign_date} à {contract.signed_at:%H:%M}"
            + (f"<br/><font size=6 color='#7D7488'>IP : {escape(contract.signed_ip)}</font>" if contract.signed_ip else ""),
            st["sig_done"])
    else:
        sig_content = None
    right = [Paragraph("Le Joueur / La Joueuse", st["card_title"]),
             Paragraph("Précédé de la mention « Lu et approuvé »", st["card_sub"]), Spacer(1, 8),
             Paragraph(f"Nom : <font name='Pop-B'>{_v(member.last_name, '______________')}</font><br/>"
                       f"Prénom : <font name='Pop-B'>{_v(member.first_name, '______________')}</font><br/>"
                       f"Gamertag : <font name='Pop-B'>{escape(member.nickname)}</font>", st["card_text"]),
             Spacer(1, 8), Paragraph("Signature :", st["sig_label"]), Spacer(1, 2), _box(84, sig_content, inner)]
    sig_row, _ = _side_by_side(_card(left, PURPLE, half), _card(right, ORANGE, half))
    story.append(KeepTogether([
        CondPageBreak(330), Spacer(1, 12), SectionBar(f"{next_no:02d}", "Signatures"), Spacer(1, 8),
        Paragraph("Fait en deux (2) exemplaires originaux, un pour chaque Partie.<br/>"
                  f"{place} le {sign_date}", st["intro"]),
        Spacer(1, 12), sig_row,
    ]))

    # --- Représentant légal ---
    full = " ".join(x for x in (member.first_name, member.last_name) if x) or "______________"
    g_left = [Paragraph(f"Nom : {_v(member.guardian_name, BLANK_SHORT)}", st["card_text"]), Spacer(1, 8),
              Paragraph(f"Lien de parenté : {_v(member.guardian_relation, BLANK_SHORT)}", st["card_text"])]
    g_sig = None
    if signed and member.guardian_name:
        g_sig = Paragraph(f"Autorisation donnée en ligne<br/>le {sign_date}", st["sig_done"])
    g_right = [Paragraph("Signature :", st["sig_label"]), Spacer(1, 2), _box(48, g_sig, inner)]
    g_row, _ = _side_by_side(_card(g_left, None, half), _card(g_right, None, half))
    story.append(KeepTogether([
        Spacer(1, 22), SectionBar(f"{next_no + 1:02d}", "Joueurs mineurs — Représentant légal"), Spacer(1, 8),
        Paragraph(f"Je soussigné(e), {_v(member.guardian_name)}, en qualité de représentant légal de "
                  f"{escape(full)}, autorise mon enfant à signer le présent Contrat.",
                  ParagraphStyle("gi", parent=st["intro"], alignment=TA_JUSTIFY)),
        Spacer(1, 12), g_row,
    ]))
    if signed:
        story += [Spacer(1, 14), Paragraph(
            "Signature électronique simple : le Joueur a validé le présent Contrat en ligne depuis son espace "
            f"personnel le {sign_date} à {contract.signed_at:%H:%M}.", st["sig_label"])]

    doc.build(story)
    return buf.getvalue()
