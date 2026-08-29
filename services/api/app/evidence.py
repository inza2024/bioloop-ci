from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .models import EvidenceCategory


MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
ALLOWED_MEDIA_TYPES = {
    "image/jpeg": {"extensions": {".jpg", ".jpeg"}, "magic": (b"\xff\xd8\xff",)},
    "image/png": {"extensions": {".png"}, "magic": (b"\x89PNG\r\n\x1a\n",)},
    "application/pdf": {"extensions": {".pdf"}, "magic": (b"%PDF-",)},
}
STORAGE_NAME_PATTERN = re.compile(r"^EVID-[A-F0-9]{24}\.(?:jpg|png|pdf)$")


class EvidenceValidationError(ValueError):
    pass


@dataclass(frozen=True)
class StoredEvidence:
    id: str
    category: EvidenceCategory
    original_filename: str
    storage_name: str
    media_type: str
    size_bytes: int
    sha256: str
    captured_at: datetime | None
    note: str


class EvidenceStorage:
    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_filename(original_filename: str, media_type: str) -> tuple[str, str]:
        filename = unicodedata.normalize("NFC", original_filename.strip())
        if not filename or len(filename) > 180:
            raise EvidenceValidationError("Le nom du fichier est vide ou trop long.")
        if any(ord(character) < 32 for character in filename):
            raise EvidenceValidationError("Le nom du fichier contient un caractère interdit.")
        if "/" in filename or "\\" in filename or filename in {".", ".."}:
            raise EvidenceValidationError("La traversée de répertoires est interdite.")
        extension = Path(filename).suffix.lower()
        allowed_extensions = ALLOWED_MEDIA_TYPES[media_type]["extensions"]
        if extension not in allowed_extensions:
            raise EvidenceValidationError(
                "L'extension ne correspond pas au type JPEG, PNG ou PDF autorisé."
            )
        normalized_extension = ".jpg" if media_type == "image/jpeg" else extension
        return filename, normalized_extension

    @staticmethod
    def _validate_content(content: bytes, media_type: str) -> None:
        if not content:
            raise EvidenceValidationError("Le fichier est vide.")
        if len(content) > MAX_EVIDENCE_BYTES:
            raise EvidenceValidationError("Le fichier dépasse la limite de 5 Mo.")
        signatures = ALLOWED_MEDIA_TYPES[media_type]["magic"]
        if not any(content.startswith(signature) for signature in signatures):
            raise EvidenceValidationError(
                "La signature du fichier ne correspond pas au type MIME déclaré."
            )

    def store(
        self,
        *,
        category: EvidenceCategory,
        original_filename: str,
        media_type: str,
        content: bytes,
        captured_at: datetime | None,
        note: str,
    ) -> StoredEvidence:
        normalized_media_type = media_type.split(";", 1)[0].strip().lower()
        if normalized_media_type not in ALLOWED_MEDIA_TYPES:
            raise EvidenceValidationError(
                "Type MIME non autorisé. Utilisez JPEG, PNG ou PDF."
            )
        filename, extension = self._validate_filename(
            original_filename, normalized_media_type
        )
        self._validate_content(content, normalized_media_type)

        evidence_id = f"EVID-{uuid4().hex[:24].upper()}"
        storage_name = f"{evidence_id}{extension}"
        target = (self.storage_dir / storage_name).resolve()
        storage_root = self.storage_dir.resolve()
        if target.parent != storage_root or not STORAGE_NAME_PATTERN.fullmatch(storage_name):
            raise EvidenceValidationError("Nom de stockage interne invalide.")
        with target.open("xb") as stream:
            stream.write(content)
        return StoredEvidence(
            id=evidence_id,
            category=category,
            original_filename=filename,
            storage_name=storage_name,
            media_type=normalized_media_type,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            captured_at=captured_at,
            note=note,
        )

    def discard(self, storage_name: str) -> None:
        if not STORAGE_NAME_PATTERN.fullmatch(storage_name):
            return
        target = (self.storage_dir / storage_name).resolve()
        if target.parent == self.storage_dir.resolve() and target.is_file():
            target.unlink()
