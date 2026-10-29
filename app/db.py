"""Connexion à la base SQLite."""

import os
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("APP_DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "structure.db"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db() -> None:
    from . import models  # noqa: F401  (enregistre les tables)

    SQLModel.metadata.create_all(engine)
    _migrate()


def _migrate() -> None:
    """Ajoute les colonnes apparues après la création de la base (SQLite)."""
    added = {
        "user": {"pending": "BOOLEAN NOT NULL DEFAULT 0"},
        "member": {"birth_place": "VARCHAR", "address": "VARCHAR", "postal_city": "VARCHAR", "platform": "VARCHAR",
                   "rank": "VARCHAR", "guardian_name": "VARCHAR", "guardian_relation": "VARCHAR"},
        "contract": {
            "status": "VARCHAR NOT NULL DEFAULT 'brouillon'",
            "clauses": "VARCHAR",
            "signed_name": "VARCHAR",
            "signed_at": "DATETIME",
            "signed_ip": "VARCHAR",
            "attachment": "VARCHAR",
            "attachment_name": "VARCHAR",
        },
    }
    with engine.begin() as conn:
        for table, columns in added.items():
            existing = {row[1] for row in conn.exec_driver_sql(f'PRAGMA table_info("{table}")')}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE "{table}" ADD COLUMN {name} {ddl}')


def get_session():
    with Session(engine) as session:
        yield session
