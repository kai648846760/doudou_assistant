"""Database utilities for SQLite persistence using SQLModel."""

from __future__ import annotations

import pathlib
from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

DB_PATH = pathlib.Path("data/douyin.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create tables if they are missing."""

    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope for database operations."""

    with Session(engine) as session:
        yield session


def get_session() -> Session:
    """Return a SQLModel session bound to the engine."""

    return Session(engine)


def reset_database() -> None:
    """Drop and recreate all tables (useful for tests)."""

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


# Ensure tables are created when the module is imported.
init_db()
