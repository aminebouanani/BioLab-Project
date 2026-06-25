"""Database setup for the local AI backend."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_backend.app.models.db_models import Base


def _ensure_sqlite_parent(database_url):
    if not database_url.startswith("sqlite:///") or database_url == "sqlite:///:memory:":
        return
    raw_path = database_url.replace("sqlite:///", "", 1)
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)


def create_session_factory(database_url):
    _ensure_sqlite_parent(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True), engine
