from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: Path
    evidence_dir: Path
    fixtures_dir: Path
    factor_set_path: Path
    web_origin: str
    database_url: str | None = None
    cookie_secure: bool = False
    session_ttl_seconds: int = 28_800
    demo_identities_enabled: bool = True
    synthetic_profile: str = "small"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.db_path.as_posix()}"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=_project_path(
                os.getenv("BIOLOOP_DB_PATH", "data/local/bioloop.db")
            ),
            evidence_dir=_project_path(
                os.getenv("BIOLOOP_EVIDENCE_DIR", "data/local/evidence")
            ),
            fixtures_dir=PROJECT_ROOT / "data" / "fixtures",
            factor_set_path=(
                PROJECT_ROOT
                / "data"
                / "factor_sets"
                / "illustrative-normalized-v1.json"
            ),
            web_origin=os.getenv(
                "BIOLOOP_WEB_ORIGIN", "http://localhost:3000"
            ),
            database_url=os.getenv("DATABASE_URL") or None,
            cookie_secure=_env_bool("BIOLOOP_COOKIE_SECURE", False),
            session_ttl_seconds=int(
                os.getenv("BIOLOOP_SESSION_TTL_SECONDS", "28800")
            ),
            demo_identities_enabled=_env_bool(
                "BIOLOOP_DEMO_IDENTITIES_ENABLED", True
            ),
            synthetic_profile=os.getenv("BIOLOOP_SYNTHETIC_PROFILE", "small"),
        )
