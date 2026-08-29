from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    fixtures_dir: Path
    factor_set_path: Path
    web_origin: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=_project_path(
                os.getenv("BIOLOOP_DB_PATH", "data/local/bioloop.db")
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
        )

