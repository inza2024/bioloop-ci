from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from .evidence import StoredEvidence
from .models import (
    AuditEventRecord,
    EstimateLineage,
    EstimateRunSummary,
    EvidenceLabel,
    EvidenceRecord,
    LotDecisionCreate,
    LotDecisionRecord,
    LotRecord,
    LotStatusEvent,
    MeasurementCreate,
    MeasurementRecord,
    ProofLevel,
    Provenance,
    WasteDeclaration,
    WasteDeclarationCreate,
)


DEMO_UNIT_ACTOR = "Opérateur unité — démonstration non authentifiée"


class RepositoryConflictError(RuntimeError):
    pass


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

    @staticmethod
    def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
        return {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }

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

                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    declaration_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    storage_name TEXT NOT NULL UNIQUE,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    captured_at TEXT,
                    note TEXT NOT NULL,
                    FOREIGN KEY (declaration_id) REFERENCES waste_declarations(id)
                );

                CREATE TABLE IF NOT EXISTS measurements (
                    id TEXT PRIMARY KEY,
                    declaration_id TEXT NOT NULL,
                    quantity_kg TEXT NOT NULL,
                    unit TEXT NOT NULL CHECK (unit = 'kg'),
                    method TEXT NOT NULL,
                    measured_at TEXT NOT NULL,
                    device_reference TEXT,
                    evidence_id TEXT,
                    supersedes_measurement_id TEXT,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (declaration_id) REFERENCES waste_declarations(id),
                    FOREIGN KEY (evidence_id) REFERENCES evidence(id),
                    FOREIGN KEY (supersedes_measurement_id) REFERENCES measurements(id)
                );

                CREATE TABLE IF NOT EXISTS lots (
                    id TEXT PRIMARY KEY,
                    declaration_id TEXT NOT NULL,
                    measurement_id TEXT NOT NULL,
                    processing_unit_id TEXT NOT NULL,
                    waste_type_id TEXT NOT NULL,
                    measured_quantity_kg TEXT NOT NULL,
                    quantity_unit TEXT NOT NULL CHECK (quantity_unit = 'kg'),
                    status TEXT NOT NULL CHECK (status IN ('lot_created', 'accepted', 'refused')),
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (declaration_id) REFERENCES waste_declarations(id),
                    FOREIGN KEY (measurement_id) REFERENCES measurements(id)
                );

                CREATE TABLE IF NOT EXISTS lot_evidence (
                    lot_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    PRIMARY KEY (lot_id, evidence_id),
                    FOREIGN KEY (lot_id) REFERENCES lots(id),
                    FOREIGN KEY (evidence_id) REFERENCES evidence(id)
                );

                CREATE TABLE IF NOT EXISTS lot_decisions (
                    id TEXT PRIMARY KEY,
                    lot_id TEXT NOT NULL UNIQUE,
                    processing_unit_id TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'refused')),
                    decided_at TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    note TEXT NOT NULL,
                    actor_label TEXT NOT NULL,
                    actor_authenticated INTEGER NOT NULL CHECK (actor_authenticated = 0),
                    FOREIGN KEY (lot_id) REFERENCES lots(id)
                );

                CREATE TABLE IF NOT EXISTS lot_status_events (
                    id TEXT PRIMARY KEY,
                    lot_id TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('measured', 'lot_created', 'accepted', 'refused')),
                    occurred_at TEXT NOT NULL,
                    actor_label TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    FOREIGN KEY (lot_id) REFERENCES lots(id)
                );

                CREATE TABLE IF NOT EXISTS estimate_lineage (
                    child_estimate_run_id TEXT PRIMARY KEY,
                    parent_estimate_run_id TEXT NOT NULL,
                    source_measurement_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (child_estimate_run_id) REFERENCES estimate_runs(id),
                    FOREIGN KEY (parent_estimate_run_id) REFERENCES estimate_runs(id),
                    FOREIGN KEY (source_measurement_id) REFERENCES measurements(id)
                );
                """
            )
            if "declaration_id" not in self._columns(connection, "audit_events"):
                connection.execute("ALTER TABLE audit_events ADD COLUMN declaration_id TEXT")
            connection.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_evidence_declaration
                    ON evidence(declaration_id, submitted_at);
                CREATE INDEX IF NOT EXISTS idx_measurements_declaration
                    ON measurements(declaration_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_lots_declaration
                    ON lots(declaration_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_estimates_declaration
                    ON estimate_runs(declaration_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_audit_declaration
                    ON audit_events(declaration_id, created_at);
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
        declaration = self.get_declaration(declaration_id)
        assert declaration is not None
        return declaration

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

    def create_evidence(
        self, declaration_id: str, stored: StoredEvidence
    ) -> EvidenceRecord:
        submitted_at = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence (
                    id, declaration_id, category, original_filename, storage_name,
                    media_type, size_bytes, sha256, submitted_at, captured_at, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.id,
                    declaration_id,
                    stored.category,
                    stored.original_filename,
                    stored.storage_name,
                    stored.media_type,
                    stored.size_bytes,
                    stored.sha256,
                    submitted_at.isoformat(),
                    stored.captured_at.isoformat() if stored.captured_at else None,
                    stored.note,
                ),
            )
        evidence = self.get_evidence(stored.id)
        assert evidence is not None
        return evidence

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM evidence WHERE id = ?", (evidence_id,)
            ).fetchone()
        return self._to_evidence(row) if row else None

    def list_evidence(self, declaration_id: str) -> list[EvidenceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence WHERE declaration_id = ? ORDER BY submitted_at",
                (declaration_id,),
            ).fetchall()
        return [self._to_evidence(row) for row in rows]

    @staticmethod
    def _to_evidence(row: sqlite3.Row) -> EvidenceRecord:
        return EvidenceRecord(
            id=row["id"],
            declaration_id=row["declaration_id"],
            category=row["category"],
            original_filename=row["original_filename"],
            media_type=row["media_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            submitted_at=row["submitted_at"],
            captured_at=row["captured_at"],
            note=row["note"],
        )

    def create_measurement(
        self, declaration_id: str, data: MeasurementCreate
    ) -> MeasurementRecord:
        measurement_id = f"MEAS-{uuid4().hex[:12].upper()}"
        created_at = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO measurements (
                    id, declaration_id, quantity_kg, unit, method, measured_at,
                    device_reference, evidence_id, supersedes_measurement_id,
                    note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    measurement_id,
                    declaration_id,
                    str(data.quantity_kg),
                    data.unit,
                    data.method,
                    data.measured_at.isoformat(),
                    data.device_reference,
                    data.evidence_id,
                    data.supersedes_measurement_id,
                    data.note,
                    created_at.isoformat(),
                ),
            )
        measurement = self.get_measurement(measurement_id)
        assert measurement is not None
        return measurement

    def get_measurement(self, measurement_id: str) -> MeasurementRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM measurements WHERE id = ?", (measurement_id,)
            ).fetchone()
        return self._to_measurement(row) if row else None

    def list_measurements(self, declaration_id: str) -> list[MeasurementRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM measurements WHERE declaration_id = ? ORDER BY created_at",
                (declaration_id,),
            ).fetchall()
        return [self._to_measurement(row) for row in rows]

    @staticmethod
    def _to_measurement(row: sqlite3.Row) -> MeasurementRecord:
        return MeasurementRecord(
            id=row["id"],
            declaration_id=row["declaration_id"],
            quantity_kg=Decimal(row["quantity_kg"]),
            unit=row["unit"],
            method=row["method"],
            measured_at=row["measured_at"],
            device_reference=row["device_reference"],
            evidence_id=row["evidence_id"],
            supersedes_measurement_id=row["supersedes_measurement_id"],
            note=row["note"],
            created_at=row["created_at"],
        )

    def create_lot(
        self,
        *,
        declaration: WasteDeclaration,
        measurement: MeasurementRecord,
        processing_unit_id: str,
        evidence_ids: list[str],
    ) -> LotRecord:
        lot_id = f"LOT-{uuid4().hex[:12].upper()}"
        created_at = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO lots (
                    id, declaration_id, measurement_id, processing_unit_id,
                    waste_type_id, measured_quantity_kg, quantity_unit, status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'kg', 'lot_created', ?)
                """,
                (
                    lot_id,
                    declaration.id,
                    measurement.id,
                    processing_unit_id,
                    declaration.waste_type_id,
                    str(measurement.quantity_kg),
                    created_at.isoformat(),
                ),
            )
            connection.executemany(
                "INSERT INTO lot_evidence (lot_id, evidence_id) VALUES (?, ?)",
                [(lot_id, evidence_id) for evidence_id in evidence_ids],
            )
            connection.executemany(
                """
                INSERT INTO lot_status_events (
                    id, lot_id, status, occurred_at, actor_label, detail
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        f"STATUS-{uuid4().hex[:12].upper()}",
                        lot_id,
                        "measured",
                        measurement.measured_at.isoformat(),
                        "Source de mesure P3 déclarée",
                        f"Mesure immuable {measurement.id} — {measurement.quantity_kg} kg",
                    ),
                    (
                        f"STATUS-{uuid4().hex[:12].upper()}",
                        lot_id,
                        "lot_created",
                        created_at.isoformat(),
                        "BioLoop CI — démonstration",
                        "Lot créé à partir de la mesure P3 sans modifier celle-ci.",
                    ),
                ],
            )
        lot = self.get_lot(lot_id)
        assert lot is not None
        return lot

    def get_lot(self, lot_id: str) -> LotRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM lots WHERE id = ?", (lot_id,)).fetchone()
        return self._to_lot(row) if row else None

    def list_lots(self, declaration_id: str) -> list[LotRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM lots WHERE declaration_id = ? ORDER BY created_at",
                (declaration_id,),
            ).fetchall()
        return [self._to_lot(row) for row in rows]

    def _to_lot(self, row: sqlite3.Row) -> LotRecord:
        with self._connect() as connection:
            evidence_ids = [
                item["evidence_id"]
                for item in connection.execute(
                    "SELECT evidence_id FROM lot_evidence WHERE lot_id = ? ORDER BY evidence_id",
                    (row["id"],),
                ).fetchall()
            ]
        return LotRecord(
            id=row["id"],
            declaration_id=row["declaration_id"],
            measurement_id=row["measurement_id"],
            processing_unit_id=row["processing_unit_id"],
            waste_type_id=row["waste_type_id"],
            measured_quantity_kg=Decimal(row["measured_quantity_kg"]),
            quantity_unit=row["quantity_unit"],
            evidence_ids=evidence_ids,
            status=row["status"],
            created_at=row["created_at"],
            decision=self.get_lot_decision(row["id"]),
            status_history=self.list_lot_status_events(row["id"]),
        )

    def record_lot_decision(
        self, lot: LotRecord, data: LotDecisionCreate
    ) -> LotDecisionRecord:
        decision_id = f"DEC-{uuid4().hex[:12].upper()}"
        decided_at = datetime.now(UTC)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "UPDATE lots SET status = ? WHERE id = ? AND status = 'lot_created'",
                    (data.decision, lot.id),
                )
                if cursor.rowcount != 1:
                    raise RepositoryConflictError(
                        "Une décision existe déjà pour ce lot et ne peut pas être écrasée."
                    )
                connection.execute(
                    """
                    INSERT INTO lot_decisions (
                        id, lot_id, processing_unit_id, decision, decided_at,
                        reason, note, actor_label, actor_authenticated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        decision_id,
                        lot.id,
                        lot.processing_unit_id,
                        data.decision,
                        decided_at.isoformat(),
                        data.reason,
                        data.note,
                        DEMO_UNIT_ACTOR,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO lot_status_events (
                        id, lot_id, status, occurred_at, actor_label, detail
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"STATUS-{uuid4().hex[:12].upper()}",
                        lot.id,
                        data.decision,
                        decided_at.isoformat(),
                        DEMO_UNIT_ACTOR,
                        data.reason or data.note or "Décision de démonstration enregistrée.",
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise RepositoryConflictError(
                "Une décision existe déjà pour ce lot et ne peut pas être écrasée."
            ) from exc
        decision = self.get_lot_decision(lot.id)
        assert decision is not None
        return decision

    def get_lot_decision(self, lot_id: str) -> LotDecisionRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM lot_decisions WHERE lot_id = ?", (lot_id,)
            ).fetchone()
        if row is None:
            return None
        return LotDecisionRecord(
            id=row["id"],
            lot_id=row["lot_id"],
            processing_unit_id=row["processing_unit_id"],
            decision=row["decision"],
            decided_at=row["decided_at"],
            reason=row["reason"],
            note=row["note"],
            actor_label=row["actor_label"],
            actor_authenticated=False,
        )

    def list_lot_status_events(self, lot_id: str) -> list[LotStatusEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM lot_status_events WHERE lot_id = ? ORDER BY rowid",
                (lot_id,),
            ).fetchall()
        return [
            LotStatusEvent(
                id=row["id"],
                lot_id=row["lot_id"],
                status=row["status"],
                occurred_at=row["occurred_at"],
                actor_label=row["actor_label"],
                detail=row["detail"],
            )
            for row in rows
        ]

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

    @staticmethod
    def _to_estimate_summary(row: sqlite3.Row) -> EstimateRunSummary:
        inputs = json.loads(row["input_snapshot"])
        return EstimateRunSummary(
            id=row["id"],
            processing_unit_id=row["processing_unit_id"],
            input_quantity_kg=Decimal(inputs["quantity_kg"]),
            input_proof_level=inputs.get("input_proof_level", "P1"),
            source_measurement_id=inputs.get("source_measurement_id"),
            calculation_hash=row["calculation_hash"],
            factor_set_version=row["factor_set_version"],
            created_at=row["created_at"],
        )

    def latest_estimate_run(
        self, declaration_id: str, processing_unit_id: str
    ) -> EstimateRunSummary | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM estimate_runs
                WHERE declaration_id = ? AND processing_unit_id = ?
                ORDER BY created_at DESC, id DESC LIMIT 1
                """,
                (declaration_id, processing_unit_id),
            ).fetchone()
        return self._to_estimate_summary(row) if row else None

    def list_estimate_runs(self, declaration_id: str) -> list[EstimateRunSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM estimate_runs WHERE declaration_id = ? ORDER BY created_at, id",
                (declaration_id,),
            ).fetchall()
        return [self._to_estimate_summary(row) for row in rows]

    def recalculation_exists(
        self, measurement_id: str, processing_unit_id: str
    ) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM estimate_lineage lineage
                JOIN estimate_runs run ON run.id = lineage.child_estimate_run_id
                WHERE lineage.source_measurement_id = ? AND run.processing_unit_id = ?
                """,
                (measurement_id, processing_unit_id),
            ).fetchone()
        return row is not None

    def link_estimates(
        self,
        *,
        parent_estimate_run_id: str,
        child_estimate_run_id: str,
        source_measurement_id: str,
    ) -> EstimateLineage:
        created_at = datetime.now(UTC)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO estimate_lineage (
                    child_estimate_run_id, parent_estimate_run_id,
                    source_measurement_id, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    child_estimate_run_id,
                    parent_estimate_run_id,
                    source_measurement_id,
                    created_at.isoformat(),
                ),
            )
        return EstimateLineage(
            parent_estimate_run_id=parent_estimate_run_id,
            child_estimate_run_id=child_estimate_run_id,
            source_measurement_id=source_measurement_id,
            created_at=created_at,
        )

    def list_estimate_lineage(self, declaration_id: str) -> list[EstimateLineage]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT lineage.* FROM estimate_lineage lineage
                JOIN estimate_runs child ON child.id = lineage.child_estimate_run_id
                WHERE child.declaration_id = ? ORDER BY lineage.created_at
                """,
                (declaration_id,),
            ).fetchall()
        return [
            EstimateLineage(
                parent_estimate_run_id=row["parent_estimate_run_id"],
                child_estimate_run_id=row["child_estimate_run_id"],
                source_measurement_id=row["source_measurement_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def append_audit_event(
        self,
        *,
        correlation_id: str,
        event_type: str,
        object_type: str,
        object_id: str,
        payload: dict,
        declaration_id: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, correlation_id, event_type, object_type,
                    object_id, payload, created_at, declaration_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"AUD-{uuid4().hex[:12].upper()}",
                    correlation_id,
                    event_type,
                    object_type,
                    object_id,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    datetime.now(UTC).isoformat(),
                    declaration_id,
                ),
            )

    def list_audit_events(self, declaration_id: str) -> list[AuditEventRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM audit_events
                WHERE declaration_id = ? ORDER BY created_at, id
                """,
                (declaration_id,),
            ).fetchall()
        return [
            AuditEventRecord(
                id=row["id"],
                correlation_id=row["correlation_id"],
                declaration_id=row["declaration_id"],
                event_type=row["event_type"],
                object_type=row["object_type"],
                object_id=row["object_id"],
                payload=json.loads(row["payload"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
