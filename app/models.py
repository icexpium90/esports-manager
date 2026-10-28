"""Modèles de données de la structure."""

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel

# --- Référentiels -----------------------------------------------------------

GAMES = {
    "valorant": "Valorant",
    "rocket_league": "Rocket League",
    "cs2": "Counter-Strike 2",
    "r6": "Rainbow Six Siege",
}

# Libellés des colonnes de stats selon le jeu (stat1, stat2, stat3, score)
GAME_STATS = {
    "valorant": ("Kills", "Morts", "Assists", "ACS"),
    "cs2": ("Kills", "Morts", "Assists", "ADR"),
    "r6": ("Kills", "Morts", "Assists", "Score"),
    "rocket_league": ("Buts", "Passes déc.", "Arrêts", "Score"),
}

GAME_ROLES = {
    "valorant": ["Duelist", "Initiator", "Controller", "Sentinel", "Flex", "IGL"],
    "cs2": ["Entry", "AWPer", "Rifler", "Support", "Lurker", "IGL"],
    "r6": ["Entry", "Support", "Flex", "Anchor", "Roamer", "IGL"],
    "rocket_league": ["Striker", "Midfield", "Défenseur", "Flex"],
}

USER_ROLES = {
    "admin": "Administrateur",
    "staff": "Staff",
    "joueur": "Joueur",
}

MEMBER_KINDS = {
    "joueur": "Joueur",
    "remplacant": "Remplaçant",
    "coach": "Coach",
    "analyste": "Analyste",
    "manager": "Manager",
    "autre": "Autre",
}

MEMBER_STATUS = {"actif": "Actif", "essai": "En essai", "inactif": "Inactif"}
# Statut interne d'un membre inscrit en ligne, pas encore validé (hors roster)
PENDING = "attente"
HIDDEN_STATUSES = ("inactif", PENDING)

CONTRACT_TYPES = {
    "salarie": "Salarié",
    "prestataire": "Prestataire / auto-entrepreneur",
    "benevole": "Bénévole",
    "stage": "Stage / alternance",
}

EVENT_KINDS = {
    "officiel": "Match officiel",
    "scrim": "Scrim",
    "entrainement": "Entraînement",
    "reunion": "Réunion",
    "autre": "Autre",
}

TRANSACTION_CATEGORIES = {
    "recette": {
        "sponsoring": "Sponsoring",
        "cashprize": "Cashprize",
        "merch": "Merchandising",
        "subvention": "Subvention",
        "dons": "Dons / streaming",
        "autre": "Autre recette",
    },
    "depense": {
        "salaires": "Salaires",
        "inscriptions": "Inscriptions tournois",
        "deplacements": "Déplacements / hébergement",
        "materiel": "Matériel",
        "logiciels": "Logiciels / abonnements",
        "marketing": "Marketing",
        "autre": "Autre dépense",
    },
}

SPONSOR_STATUS = {
    "prospect": "Prospect",
    "negociation": "En négociation",
    "actif": "Actif",
    "termine": "Terminé",
}


# --- Tables -----------------------------------------------------------------


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    password_hash: str
    role: str = "staff"
    member_id: Optional[int] = Field(default=None, foreign_key="member.id")
    active: bool = True
    pending: bool = False  # inscription en ligne en attente de validation
    created_at: datetime = Field(default_factory=datetime.now)


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    game: str
    description: Optional[str] = None
    active: bool = True


class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nickname: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    kind: str = "joueur"
    game_role: Optional[str] = None
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    status: str = "actif"
    email: Optional[str] = None
    phone: Optional[str] = None
    discord: Optional[str] = None
    nationality: Optional[str] = None
    birth_date: Optional[date] = None
    joined_on: Optional[date] = None
    notes: Optional[str] = None


class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    type: str = "salarie"
    start_date: date
    end_date: Optional[date] = None
    monthly_amount: float = 0
    notes: Optional[str] = None


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: Optional[int] = Field(default=None, foreign_key="team.id", index=True)
    kind: str = "scrim"
    title: Optional[str] = None
    opponent: Optional[str] = None
    competition: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    score_us: Optional[int] = None
    score_them: Optional[int] = None
    maps: Optional[str] = None


class PlayerStat(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="event.id", index=True)
    member_id: int = Field(foreign_key="member.id", index=True)
    stat1: Optional[float] = None
    stat2: Optional[float] = None
    stat3: Optional[float] = None
    score: Optional[float] = None
    rating: Optional[float] = None
    mvp: bool = False
    comment: Optional[str] = None


class Sponsor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    status: str = "prospect"
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    yearly_amount: float = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    deliverables: Optional[str] = None
    notes: Optional[str] = None


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: date
    direction: str = "depense"  # recette | depense
    category: str = "autre"
    amount: float
    label: str
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    sponsor_id: Optional[int] = Field(default=None, foreign_key="sponsor.id")
    notes: Optional[str] = None
