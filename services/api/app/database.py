from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import PROJECT_ROOT


@dataclass(frozen=True)
class GeoPoint:
    """Portable pilot representation; a PostGIS adapter can replace it later."""

    latitude: float
    longitude: float


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


class Database:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def run_migrations(database_url: str) -> None:
    alembic_path = PROJECT_ROOT / "services" / "api" / "alembic.ini"
    config = Config(str(alembic_path))
    config.set_main_option(
        "script_location", str(PROJECT_ROOT / "services" / "api" / "alembic")
    )
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
