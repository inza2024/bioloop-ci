from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from .models import (
    EvidenceLabel,
    ProofLevel,
    Provenance,
    WasteDeclaration,
    WasteDeclarationCreate,
)


class Repository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS waste_declarations (
                    id TEXT PRIMARY KEY,
                    producer_id TEXT NOT NULL,
                    producer_name TEXT NOT NULL,
                    producer_locality TEXT NOT NULL,
                    waste_type_id TEXT NOT NULL,
                    quantity_kg TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    availability_date TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS estimate_runs (
                    id TEXT PRIMARY KEY,
                    declaration_id TEXT NOT NULL,
                    processing_unit_id TEXT NOT NULL,
                    factor_set_id TEXT NOT NULL,
                    factor_set_version TEXT NOT NULL,
                    calculation_hash TEXT NOT NULL,
                    input_snapshot TEXT NOT NULL,
                    output_snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (declaration_id) REFERENCES waste_declarations(id)
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_declaration(self, data: WasteDeclarationCreate, producer) -> WasteDeclaration:
        declaration_id = f"DECL-{uuid4().hex[:12].upper()}"
        created_at = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO waste_declarations (
                    id, producer_id, producer_name, producer_locality,
                    waste_type_id, quantity_kg, frequency, availability_date,
                    notes, latitude, longitude, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    declaration_id,
                    data.producer_id,
                    producer.name,
                    producer.locality,
                    data.waste_type_id,
                    str(data.quantity_kg),
                    data.frequency,
                    data.availability_date.isoformat(),
                    data.notes,
                    producer.latitude,
                    producer.longitude,
                    created_at.isoformat(),
                ),
            )
        return self.get_declaration(declaration_id)

    def get_declaration(self, declaration_id: str) -> WasteDeclaration | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM waste_declarations WHERE id = ?", (declaration_id,)
            ).fetchone()
        return self._to_declaration(row) if row else None

    def list_declarations(self) -> list[WasteDeclaration]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM waste_declarations ORDER BY created_at DESC"
            ).fetchall()
        return [self._to_declaration(row) for row in rows]

    @staticmethod
    def _to_declaration(row: sqlite3.Row) -> WasteDeclaration:
        return WasteDeclaration(
            id=row["id"],
            producer_id=row["producer_id"],
            producer_name=row["producer_name"],
            producer_locality=row["producer_locality"],
            waste_type_id=row["waste_type_id"],
            quantity_kg=Decimal(row["quantity_kg"]),
            frequency=row["frequency"],
            availability_date=row["availability_date"],
            notes=row["notes"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            provenance=Provenance.DECLARED,
            proof_level=ProofLevel.P1,
            created_at=row["created_at"],
            field_evidence={
                "quantity_kg": EvidenceLabel(
                    provenance=Provenance.DECLARED,
                    proof_level=ProofLevel.P1,
                    label="Quantité déclarée par l'utilisateur — non pesée",
                ),
                "waste_type_id": EvidenceLabel(
                    provenance=Provenance.DECLARED,
                    proof_level=ProofLevel.P1,
                    label="Type déclaré par l'utilisateur — non contrôlé",
                ),
                "location": EvidenceLabel(
                    provenance=Provenance.SIMULATED,
                    proof_level=ProofLevel.P0,
                    label="Coordonnées fictives de démonstration",
                ),
            },
        )

    def save_estimate_run(
        self,
        *,
        estimate,
        processing_unit_id: str,
        input_snapshot: dict,
        output_snapshot: dict,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO estimate_runs (
                    id, declaration_id, processing_unit_id, factor_set_id,
                    factor_set_version, calculation_hash, input_snapshot,
                    output_snapshot, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    estimate.id,
                    estimate.declaration_id,
                    processing_unit_id,
                    estimate.factor_set_id,
                    estimate.factor_set_version,
                    estimate.calculation_hash,
                    json.dumps(input_snapshot, ensure_ascii=False, sort_keys=True),
                    json.dumps(output_snapshot, ensure_ascii=False, sort_keys=True),
                    estimate.created_at.isoformat(),
                ),
            )

    def append_audit_event(
        self,
        *,
        correlation_id: str,
        event_type: str,
        object_type: str,
        object_id: str,
        payload: dict,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, correlation_id, event_type, object_type,
                    object_id, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"AUD-{uuid4().hex[:12].upper()}",
                    correlation_id,
                    event_type,
                    object_type,
                    object_id,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                ),
            )

