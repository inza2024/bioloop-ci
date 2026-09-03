from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text

from .database import Database
from .models import DemoActor, DemoRole, ProofLevel, Provenance


ProductCategory = Literal[
    "measured_biogas",
    "raw_digestate",
    "liquid_fraction",
    "solid_fraction",
    "compost_amendment",
    "potential_fertilizing_product",
    "other_coproduct",
]
ProductUnit = Literal["kg", "L", "m3"]


class OperationsError(ValueError):
    pass


class OperationsConflictError(OperationsError):
    pass


class OperationsPermissionError(OperationsError):
    pass


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("La date doit inclure un fuseau horaire.")
    return value


class TransformationInputCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    lot_id: str = Field(pattern=r"^LOT-[A-F0-9]{12}$")
    measured_quantity: Decimal = Field(gt=0, le=100_000, max_digits=12, decimal_places=3)
    unit: Literal["kg"] = "kg"
    measurement_method: str = Field(min_length=3, max_length=120)
    measured_at: datetime
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)

    _validate_measured_at = field_validator("measured_at")(_aware)


class TransformationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    processing_unit_id: str = Field(pattern=r"^UNIT-[0-9]{3}$")
    process: str = Field(min_length=3, max_length=120)
    inputs: list[TransformationInputCreate] = Field(min_length=1, max_length=20)
    started_at: datetime | None = None

    @field_validator("started_at")
    @classmethod
    def validate_started_at(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value else None

    @model_validator(mode="after")
    def unique_lots(self) -> "TransformationCreate":
        if len({item.lot_id for item in self.inputs}) != len(self.inputs):
            raise ValueError("Chaque lot entrant doit apparaître une seule fois.")
        return self


class TransformationStatusCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: Literal["in_progress", "completed", "cancelled"]
    occurred_at: datetime
    loss_quantity: Decimal | None = Field(
        default=None, ge=0, le=100_000, max_digits=12, decimal_places=3
    )
    loss_unit: ProductUnit | None = None
    loss_method: str | None = Field(default=None, max_length=120)
    loss_measured_at: datetime | None = None

    _validate_occurred_at = field_validator("occurred_at")(_aware)

    @field_validator("loss_measured_at")
    @classmethod
    def validate_loss_measured_at(cls, value: datetime | None) -> datetime | None:
        return _aware(value) if value else None

    @model_validator(mode="after")
    def complete_loss_metadata(self) -> "TransformationStatusCreate":
        supplied = [self.loss_quantity is not None, self.loss_unit is not None, bool(self.loss_method), self.loss_measured_at is not None]
        if any(supplied) and not all(supplied):
            raise ValueError("Une perte mesurée exige quantité, unité, méthode et date.")
        return self


class ProductOutputCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: ProductCategory
    quantity: Decimal = Field(gt=0, le=1_000_000, max_digits=14, decimal_places=3)
    unit: ProductUnit
    measurement_method: str = Field(min_length=3, max_length=120)
    measured_at: datetime
    evidence_id: str | None = Field(default=None, pattern=r"^EVID-[A-F0-9]{24}$")
    location: str = Field(min_length=2, max_length=120)

    _validate_measured_at = field_validator("measured_at")(_aware)


class ProductOutputsCreate(BaseModel):
    outputs: list[ProductOutputCreate] = Field(min_length=1, max_length=20)


class QualityTestCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    parameter: str = Field(min_length=2, max_length=100)
    value: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=40)
    method: str = Field(min_length=3, max_length=160)
    laboratory_or_actor: str = Field(min_length=2, max_length=160)
    document_reference: str | None = Field(default=None, max_length=180)
    tested_at: datetime

    _validate_tested_at = field_validator("tested_at")(_aware)


class ProductReleaseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    status: Literal["released", "rejected"]
    note: str = Field(min_length=3, max_length=500)


class ReservationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    quantity: Decimal = Field(gt=0, le=1_000_000, max_digits=14, decimal_places=3)
    unit: ProductUnit
    idempotency_key: str = Field(
        min_length=8, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$"
    )


class InventoryAdjustmentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    quantity_delta: Decimal = Field(ge=-1_000_000, le=1_000_000, max_digits=14, decimal_places=3)
    unit: ProductUnit
    reason: str = Field(min_length=3, max_length=500)
    idempotency_key: str = Field(
        min_length=8, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$"
    )

    @field_validator("quantity_delta")
    @classmethod
    def non_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Un ajustement nul n’est pas un mouvement.")
        return value


class TransformationInputView(BaseModel):
    lot_id: str
    measured_quantity: Decimal
    unit: str
    measurement_method: str
    measured_at: datetime
    provenance: Provenance
    proof_level: ProofLevel


class TransformationView(BaseModel):
    id: str
    operator_organization_id: str
    processing_unit_id: str
    process: str
    status: Literal["planned", "in_progress", "completed", "cancelled"]
    started_at: datetime | None
    completed_at: datetime | None
    operator_user_id: str
    loss_quantity: Decimal | None
    loss_unit: str | None
    loss_method: str | None
    loss_measured_at: datetime | None
    loss_proof_level: ProofLevel | None
    correlation_id: str
    created_at: datetime
    inputs: list[TransformationInputView]
    evidence_ids: list[str]
    output_product_ids: list[str]
    scientific_derivation: Literal[False] = False
    measurement_warning: str = (
        "Toutes les quantités physiques sont saisies par un opérateur ; aucune URI illustrative n’est convertie."
    )


class QualityTestView(BaseModel):
    id: str
    product_batch_id: str
    parameter: str
    value: str
    unit: str
    method: str
    laboratory_or_actor: str
    document_reference: str | None
    tested_at: datetime
    actor_user_id: str
    actor_organization_id: str
    provenance: Provenance
    proof_level: ProofLevel
    correlation_id: str
    created_at: datetime


class InventoryMovementView(BaseModel):
    id: str
    product_batch_id: str
    movement_type: Literal["production", "adjustment", "reservation", "cancellation", "delivery"]
    quantity: Decimal
    unit: str
    on_hand_delta: Decimal
    reserved_delta: Decimal
    reason: str
    reservation_id: str | None
    actor_user_id: str
    actor_organization_id: str
    provenance: Provenance
    proof_level: ProofLevel
    correlation_id: str
    created_at: datetime


class ProductBatchView(BaseModel):
    id: str
    transformation_id: str
    owner_organization_id: str
    category: ProductCategory
    quantity: Decimal
    unit: ProductUnit
    measurement_method: str
    measured_at: datetime
    evidence_id: str | None
    provenance: Provenance
    proof_level: ProofLevel
    quality_status: Literal["quarantine", "pending_analysis", "released", "rejected"]
    location: str
    correlation_id: str
    created_at: datetime
    on_hand_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    quality_tests: list[QualityTestView]
    release_proof_level: ProofLevel | None = None
    quality_warning: str = (
        "Digestat et coproduits ne sont pas présentés comme engrais ou biofertilisants certifiés."
    )


class ReservationView(BaseModel):
    id: str
    product_batch_id: str
    customer_organization_id: str
    quantity: Decimal
    unit: ProductUnit
    status: Literal["active", "cancelled", "delivered"]
    idempotency_key: str
    actor_user_id: str
    correlation_id: str
    created_at: datetime
    cancelled_at: datetime | None
    delivered_at: datetime | None


class OperationsWorkspace(BaseModel):
    actor: DemoActor
    accepted_lots: list[dict] = Field(default_factory=list)
    transformations: list[TransformationView] = Field(default_factory=list)
    products: list[ProductBatchView] = Field(default_factory=list)
    reservations: list[ReservationView] = Field(default_factory=list)
    scientific_notice: str = (
        "Données synthétiques P0 ou saisies P3/P4 ; aucune validation scientifique ou certification P5."
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _sql_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class OperationsService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _require_active(actor: DemoActor) -> None:
        if actor.membership_status != "active":
            raise OperationsPermissionError("Une appartenance active est requise.")

    def _unit_id(self, actor: DemoActor) -> str:
        self._require_active(actor)
        if actor.role != DemoRole.UNIT_OPERATOR:
            raise OperationsPermissionError("Cette action est réservée à une unité de transformation.")
        if actor.site_id:
            return actor.site_id
        with self.database.session() as session:
            row = session.execute(
                text("SELECT site_id FROM pilot_organizations WHERE id = :id"),
                {"id": actor.organization_id},
            ).first()
        if row is None or not row[0]:
            raise OperationsPermissionError(
                "L’organisation unité doit être approuvée et liée à un site pilote."
            )
        return row[0]

    @staticmethod
    def _row_decimal(row, key: str) -> Decimal | None:
        value = row[key]
        return Decimal(value) if value is not None else None

    def list_accepted_lots(self, actor: DemoActor) -> list[dict]:
        unit_id = self._unit_id(actor)
        with self.database.session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT lots.id, lots.declaration_id, lots.processing_unit_id,
                           lots.waste_type_id, lots.measured_quantity_kg,
                           lots.quantity_unit, lots.created_at
                    FROM lots
                    WHERE lots.status = 'accepted'
                      AND lots.processing_unit_id = :unit_id
                      AND NOT EXISTS (
                          SELECT 1 FROM transformation_inputs inputs
                          WHERE inputs.lot_id = lots.id
                      )
                    ORDER BY lots.created_at, lots.id
                    """
                ),
                {"unit_id": unit_id},
            ).mappings().all()
            items = []
            for row in rows:
                evidence_ids = [
                    item[0]
                    for item in session.execute(
                        text(
                            """
                            SELECT evidence_id FROM lot_evidence
                            WHERE lot_id = :lot_id ORDER BY evidence_id
                            """
                        ),
                        {"lot_id": row["id"]},
                    ).all()
                ]
                items.append(
                    {
                        **dict(row),
                        "measured_quantity_kg": Decimal(row["measured_quantity_kg"]),
                        "input_provenance": Provenance.MEASURED,
                        "input_proof_level": ProofLevel.P3,
                        "evidence_ids": evidence_ids,
                    }
                )
        return items

    def create_transformation(
        self,
        data: TransformationCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> TransformationView:
        unit_id = self._unit_id(actor)
        if unit_id != data.processing_unit_id:
            raise OperationsPermissionError("Le lot doit appartenir à l’unité active.")
        transformation_id = f"TRUN-{uuid4().hex[:16].upper()}"
        created_at = _now()
        status = "in_progress" if data.started_at else "planned"
        with self.database.session() as session:
            evidence_ids: set[str] = set()
            for item in data.inputs:
                lot = session.execute(
                    text(
                        """
                        SELECT id, status, processing_unit_id, measured_quantity_kg
                        FROM lots WHERE id = :lot_id
                        """
                    ),
                    {"lot_id": item.lot_id},
                ).mappings().first()
                if lot is None:
                    raise OperationsError(f"Lot entrant introuvable : {item.lot_id}.")
                if lot["status"] != "accepted":
                    raise OperationsConflictError(
                        f"Le lot {item.lot_id} n’est pas accepté et ne peut pas être transformé."
                    )
                if lot["processing_unit_id"] != unit_id:
                    raise OperationsPermissionError("Le lot appartient à une autre unité.")
                if item.measured_quantity > Decimal(lot["measured_quantity_kg"]):
                    raise OperationsError(
                        "La masse d’entrée mesurée ne peut dépasser la masse P3 du lot accepté."
                    )
                existing = session.execute(
                    text("SELECT 1 FROM transformation_inputs WHERE lot_id = :lot_id"),
                    {"lot_id": item.lot_id},
                ).first()
                if existing:
                    raise OperationsConflictError("Ce lot est déjà affecté à une transformation.")
                for evidence_id in item.evidence_ids:
                    linked = session.execute(
                        text(
                            """
                            SELECT 1 FROM lot_evidence
                            WHERE lot_id = :lot_id AND evidence_id = :evidence_id
                            """
                        ),
                        {"lot_id": item.lot_id, "evidence_id": evidence_id},
                    ).first()
                    if linked is None:
                        raise OperationsError(
                            "Chaque preuve de transformation doit provenir d’un lot entrant."
                        )
                    evidence_ids.add(evidence_id)
            session.execute(
                text(
                    """
                    INSERT INTO transformation_runs
                        (id, operator_organization_id, processing_unit_id, process,
                         status, started_at, completed_at, operator_user_id,
                         loss_quantity, loss_unit, loss_method, loss_measured_at,
                         loss_proof_level, correlation_id, created_at)
                    VALUES (:id, :organization_id, :unit_id, :process, :status,
                            :started_at, NULL, :operator_user_id,
                            NULL, NULL, NULL, NULL, NULL, :correlation_id, :created_at)
                    """
                ),
                {
                    "id": transformation_id,
                    "organization_id": actor.organization_id,
                    "unit_id": unit_id,
                    "process": data.process,
                    "status": status,
                    "started_at": _sql_datetime(data.started_at),
                    "operator_user_id": actor.user_id,
                    "correlation_id": correlation_id,
                    "created_at": _sql_datetime(created_at),
                },
            )
            for item in data.inputs:
                session.execute(
                    text(
                        """
                        INSERT INTO transformation_inputs
                            (transformation_id, lot_id, measured_quantity,
                             quantity_unit, measurement_method, measured_at,
                             provenance, proof_level)
                        VALUES (:transformation_id, :lot_id, :quantity, :unit,
                                :method, :measured_at, 'measured', 'P3')
                        """
                    ),
                    {
                        "transformation_id": transformation_id,
                        "lot_id": item.lot_id,
                        "quantity": str(item.measured_quantity),
                        "unit": item.unit,
                        "method": item.measurement_method,
                        "measured_at": _sql_datetime(item.measured_at),
                    },
                )
            for evidence_id in sorted(evidence_ids):
                session.execute(
                    text(
                        "INSERT INTO transformation_evidence (transformation_id, evidence_id) VALUES (:transformation_id, :evidence_id)"
                    ),
                    {"transformation_id": transformation_id, "evidence_id": evidence_id},
                )
        return self.get_transformation(transformation_id)

    def get_transformation(self, transformation_id: str) -> TransformationView:
        with self.database.session() as session:
            row = session.execute(
                text("SELECT * FROM transformation_runs WHERE id = :id"),
                {"id": transformation_id},
            ).mappings().first()
            if row is None:
                raise OperationsError("Exécution de transformation introuvable.")
            inputs = session.execute(
                text(
                    """
                    SELECT lot_id, measured_quantity, quantity_unit, measurement_method,
                           measured_at, provenance, proof_level
                    FROM transformation_inputs WHERE transformation_id = :id
                    ORDER BY lot_id
                    """
                ),
                {"id": transformation_id},
            ).mappings().all()
            evidence_ids = [
                item[0]
                for item in session.execute(
                    text("SELECT evidence_id FROM transformation_evidence WHERE transformation_id = :id ORDER BY evidence_id"),
                    {"id": transformation_id},
                ).all()
            ]
            product_ids = [
                item[0]
                for item in session.execute(
                    text("SELECT id FROM product_batches WHERE transformation_id = :id ORDER BY created_at, id"),
                    {"id": transformation_id},
                ).all()
            ]
        return TransformationView(
            id=row["id"],
            operator_organization_id=row["operator_organization_id"],
            processing_unit_id=row["processing_unit_id"],
            process=row["process"],
            status=row["status"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            operator_user_id=row["operator_user_id"],
            loss_quantity=self._row_decimal(row, "loss_quantity"),
            loss_unit=row["loss_unit"],
            loss_method=row["loss_method"],
            loss_measured_at=row["loss_measured_at"],
            loss_proof_level=row["loss_proof_level"],
            correlation_id=row["correlation_id"],
            created_at=row["created_at"],
            inputs=[
                TransformationInputView(
                    lot_id=item["lot_id"],
                    measured_quantity=Decimal(item["measured_quantity"]),
                    unit=item["quantity_unit"],
                    measurement_method=item["measurement_method"],
                    measured_at=item["measured_at"],
                    provenance=item["provenance"],
                    proof_level=item["proof_level"],
                )
                for item in inputs
            ],
            evidence_ids=evidence_ids,
            output_product_ids=product_ids,
        )

    def list_transformations(self, actor: DemoActor) -> list[TransformationView]:
        self._require_active(actor)
        if actor.role == DemoRole.COORDINATOR:
            query, params = "SELECT id FROM transformation_runs ORDER BY created_at DESC", {}
        elif actor.role == DemoRole.UNIT_OPERATOR:
            self._unit_id(actor)
            query, params = (
                "SELECT id FROM transformation_runs WHERE operator_organization_id = :org ORDER BY created_at DESC",
                {"org": actor.organization_id},
            )
        else:
            return []
        with self.database.session() as session:
            ids = [row[0] for row in session.execute(text(query), params).all()]
        return [self.get_transformation(item) for item in ids]

    def update_transformation_status(
        self,
        transformation_id: str,
        data: TransformationStatusCreate,
        actor: DemoActor,
    ) -> TransformationView:
        transformation = self.get_transformation(transformation_id)
        if actor.role != DemoRole.COORDINATOR:
            self._unit_id(actor)
            if transformation.operator_organization_id != actor.organization_id:
                raise OperationsPermissionError("Cette transformation appartient à une autre organisation.")
        transitions = {
            "planned": {"in_progress", "cancelled"},
            "in_progress": {"completed", "cancelled"},
            "completed": set(),
            "cancelled": set(),
        }
        if data.status not in transitions[transformation.status]:
            raise OperationsConflictError("Transition de statut de transformation interdite.")
        if data.status == "completed" and not transformation.output_product_ids:
            raise OperationsConflictError(
                "Enregistrez au moins une sortie physique mesurée avant de terminer."
            )
        if data.loss_quantity is not None and data.loss_unit == "kg":
            total_input_kg = sum(
                item.measured_quantity for item in transformation.inputs if item.unit == "kg"
            )
            if data.loss_quantity > total_input_kg:
                raise OperationsError("La perte mesurée ne peut dépasser les entrées comparables en kg.")
        with self.database.session() as session:
            session.execute(
                text(
                    """
                    UPDATE transformation_runs
                    SET status = :status,
                        started_at = CASE WHEN :status = 'in_progress' THEN :occurred_at ELSE started_at END,
                        completed_at = CASE WHEN :status IN ('completed', 'cancelled') THEN :occurred_at ELSE completed_at END,
                        loss_quantity = :loss_quantity,
                        loss_unit = :loss_unit,
                        loss_method = :loss_method,
                        loss_measured_at = :loss_measured_at,
                        loss_proof_level = CASE WHEN :loss_quantity IS NULL THEN NULL ELSE 'P3' END
                    WHERE id = :id
                    """
                ),
                {
                    "status": data.status,
                    "occurred_at": _sql_datetime(data.occurred_at),
                    "loss_quantity": str(data.loss_quantity) if data.loss_quantity is not None else None,
                    "loss_unit": data.loss_unit,
                    "loss_method": data.loss_method,
                    "loss_measured_at": _sql_datetime(data.loss_measured_at),
                    "id": transformation_id,
                },
            )
        return self.get_transformation(transformation_id)

    def _insert_movement(
        self,
        session,
        *,
        product_id: str,
        movement_type: str,
        quantity: Decimal,
        unit: str,
        on_hand_delta: Decimal,
        reserved_delta: Decimal,
        reason: str,
        reservation_id: str | None,
        idempotency_key: str,
        actor: DemoActor,
        proof_level: ProofLevel,
        correlation_id: str,
    ) -> str:
        movement_id = f"MOVE-{uuid4().hex[:16].upper()}"
        session.execute(
            text(
                """
                INSERT INTO inventory_movements
                    (id, product_batch_id, movement_type, quantity, unit,
                     on_hand_delta, reserved_delta, reason, reservation_id,
                     idempotency_key, actor_user_id, actor_organization_id,
                     provenance, proof_level, correlation_id, created_at)
                VALUES (:id, :product_id, :movement_type, :quantity, :unit,
                        :on_hand_delta, :reserved_delta, :reason, :reservation_id,
                        :idempotency_key, :actor_user_id, :actor_organization_id,
                        :provenance, :proof_level, :correlation_id, :created_at)
                """
            ),
            {
                "id": movement_id,
                "product_id": product_id,
                "movement_type": movement_type,
                "quantity": str(quantity),
                "unit": unit,
                "on_hand_delta": str(on_hand_delta),
                "reserved_delta": str(reserved_delta),
                "reason": reason,
                "reservation_id": reservation_id,
                "idempotency_key": idempotency_key,
                "actor_user_id": actor.user_id,
                "actor_organization_id": actor.organization_id,
                "provenance": (
                    Provenance.DECLARED.value
                    if proof_level == ProofLevel.P1
                    else Provenance.MEASURED.value
                ),
                "proof_level": proof_level.value,
                "correlation_id": correlation_id,
                "created_at": _sql_datetime(_now()),
            },
        )
        return movement_id

    def create_outputs(
        self,
        transformation_id: str,
        data: ProductOutputsCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> list[ProductBatchView]:
        transformation = self.get_transformation(transformation_id)
        self._unit_id(actor)
        if transformation.operator_organization_id != actor.organization_id:
            raise OperationsPermissionError("Cette transformation appartient à une autre organisation.")
        if transformation.status not in {"in_progress", "completed"}:
            raise OperationsConflictError(
                "La transformation doit être en cours avant la saisie des sorties."
            )
        input_kg = sum(item.measured_quantity for item in transformation.inputs if item.unit == "kg")
        new_kg = sum(item.quantity for item in data.outputs if item.unit == "kg")
        with self.database.session() as session:
            existing_kg = sum(
                Decimal(row[0])
                for row in session.execute(
                    text("SELECT quantity FROM product_batches WHERE transformation_id = :id AND unit = 'kg'"),
                    {"id": transformation_id},
                ).all()
            )
            loss_kg = transformation.loss_quantity or Decimal("0")
            if existing_kg + new_kg + loss_kg > input_kg:
                raise OperationsError(
                    "Les sorties et pertes exprimées en kg dépassent les entrées mesurées comparables."
                )
            product_ids: list[str] = []
            for item in data.outputs:
                if item.evidence_id and item.evidence_id not in transformation.evidence_ids:
                    raise OperationsError(
                        "La preuve produit doit être associée à la transformation source."
                    )
                product_id = f"PRODLOT-{uuid4().hex[:16].upper()}"
                product_ids.append(product_id)
                session.execute(
                    text(
                        """
                        INSERT INTO product_batches
                            (id, transformation_id, owner_organization_id, category,
                             quantity, unit, measurement_method, measured_at,
                             evidence_id, provenance, proof_level, quality_status,
                             location, correlation_id, created_at)
                        VALUES (:id, :transformation_id, :owner_organization_id,
                                :category, :quantity, :unit, :measurement_method,
                                :measured_at, :evidence_id, 'measured', 'P3',
                                'quarantine', :location, :correlation_id, :created_at)
                        """
                    ),
                    {
                        "id": product_id,
                        "transformation_id": transformation_id,
                        "owner_organization_id": actor.organization_id,
                        "category": item.category,
                        "quantity": str(item.quantity),
                        "unit": item.unit,
                        "measurement_method": item.measurement_method,
                        "measured_at": _sql_datetime(item.measured_at),
                        "evidence_id": item.evidence_id,
                        "location": item.location,
                        "correlation_id": correlation_id,
                        "created_at": _sql_datetime(_now()),
                    },
                )
                self._insert_movement(
                    session,
                    product_id=product_id,
                    movement_type="production",
                    quantity=item.quantity,
                    unit=item.unit,
                    on_hand_delta=item.quantity,
                    reserved_delta=Decimal("0"),
                    reason="Quantité physique explicitement mesurée et enregistrée par l’opérateur.",
                    reservation_id=None,
                    idempotency_key=f"production:{product_id}",
                    actor=actor,
                    proof_level=ProofLevel.P3,
                    correlation_id=correlation_id,
                )
        return [self.get_product(item) for item in product_ids]

    def _balance(self, session, product_id: str) -> tuple[Decimal, Decimal, Decimal]:
        rows = session.execute(
            text(
                "SELECT on_hand_delta, reserved_delta FROM inventory_movements WHERE product_batch_id = :id"
            ),
            {"id": product_id},
        ).all()
        on_hand = sum((Decimal(row[0]) for row in rows), Decimal("0"))
        reserved = sum((Decimal(row[1]) for row in rows), Decimal("0"))
        return on_hand, reserved, on_hand - reserved

    def _quality_tests(self, session, product_id: str) -> list[QualityTestView]:
        rows = session.execute(
            text("SELECT * FROM product_quality_tests WHERE product_batch_id = :id ORDER BY tested_at, id"),
            {"id": product_id},
        ).mappings().all()
        return [QualityTestView.model_validate(dict(row)) for row in rows]

    def get_product(self, product_id: str) -> ProductBatchView:
        with self.database.session() as session:
            row = session.execute(
                text("SELECT * FROM product_batches WHERE id = :id"), {"id": product_id}
            ).mappings().first()
            if row is None:
                raise OperationsError("Lot produit introuvable.")
            on_hand, reserved, available = self._balance(session, product_id)
            tests = self._quality_tests(session, product_id)
            release = session.execute(
                text(
                    "SELECT proof_level FROM product_release_events WHERE product_batch_id = :id ORDER BY created_at DESC LIMIT 1"
                ),
                {"id": product_id},
            ).first()
        payload = dict(row)
        payload["quantity"] = Decimal(row["quantity"])
        return ProductBatchView(
            **payload,
            on_hand_quantity=on_hand,
            reserved_quantity=reserved,
            available_quantity=available,
            quality_tests=tests,
            release_proof_level=release[0] if release else None,
        )

    def list_products(self, actor: DemoActor) -> list[ProductBatchView]:
        self._require_active(actor)
        clauses, params = [], {}
        if actor.role == DemoRole.UNIT_OPERATOR:
            self._unit_id(actor)
            clauses.append("owner_organization_id = :organization_id")
            params["organization_id"] = actor.organization_id
        elif actor.role == DemoRole.CLIENT:
            clauses.append("quality_status = 'released'")
        elif actor.role not in {DemoRole.FIELD_CONTROLLER, DemoRole.COORDINATOR}:
            return []
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.database.session() as session:
            ids = [
                row[0]
                for row in session.execute(
                    text(f"SELECT id FROM product_batches {where} ORDER BY created_at DESC"), params
                ).all()
            ]
        products = [self.get_product(item) for item in ids]
        if actor.role == DemoRole.CLIENT:
            return [item for item in products if item.available_quantity > 0]
        return products

    def add_quality_test(
        self,
        product_id: str,
        data: QualityTestCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> QualityTestView:
        product = self.get_product(product_id)
        self._require_active(actor)
        if actor.role == DemoRole.UNIT_OPERATOR:
            self._unit_id(actor)
            if product.owner_organization_id != actor.organization_id:
                raise OperationsPermissionError("Ce produit appartient à une autre unité.")
            proof_level = ProofLevel.P3
        elif actor.role == DemoRole.FIELD_CONTROLLER:
            proof_level = ProofLevel.P4
        elif actor.role == DemoRole.COORDINATOR:
            proof_level = ProofLevel.P3
        else:
            raise OperationsPermissionError("Ce rôle ne peut pas enregistrer une analyse qualité.")
        if product.quality_status in {"released", "rejected"}:
            raise OperationsConflictError("La décision qualité finale est déjà enregistrée.")
        quality_id = f"QTEST-{uuid4().hex[:16].upper()}"
        created_at = _now()
        with self.database.session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO product_quality_tests
                        (id, product_batch_id, parameter, value, unit, method,
                         laboratory_or_actor, document_reference, tested_at,
                         actor_user_id, actor_organization_id, provenance,
                         proof_level, correlation_id, created_at)
                    VALUES (:id, :product_id, :parameter, :value, :unit, :method,
                            :laboratory, :document, :tested_at, :actor_user_id,
                            :actor_organization_id, :provenance, :proof_level,
                            :correlation_id, :created_at)
                    """
                ),
                {
                    "id": quality_id,
                    "product_id": product_id,
                    "parameter": data.parameter,
                    "value": data.value,
                    "unit": data.unit,
                    "method": data.method,
                    "laboratory": data.laboratory_or_actor,
                    "document": data.document_reference,
                    "tested_at": _sql_datetime(data.tested_at),
                    "actor_user_id": actor.user_id,
                    "actor_organization_id": actor.organization_id,
                    "provenance": Provenance.VERIFIED.value if proof_level == ProofLevel.P4 else Provenance.MEASURED.value,
                    "proof_level": proof_level.value,
                    "correlation_id": correlation_id,
                    "created_at": _sql_datetime(created_at),
                },
            )
            session.execute(
                text("UPDATE product_batches SET quality_status = 'pending_analysis' WHERE id = :id"),
                {"id": product_id},
            )
        return QualityTestView(
            id=quality_id,
            product_batch_id=product_id,
            parameter=data.parameter,
            value=data.value,
            unit=data.unit,
            method=data.method,
            laboratory_or_actor=data.laboratory_or_actor,
            document_reference=data.document_reference,
            tested_at=data.tested_at,
            actor_user_id=actor.user_id,
            actor_organization_id=actor.organization_id,
            provenance=Provenance.VERIFIED if proof_level == ProofLevel.P4 else Provenance.MEASURED,
            proof_level=proof_level,
            correlation_id=correlation_id,
            created_at=created_at,
        )

    def release_product(
        self,
        product_id: str,
        data: ProductReleaseCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> ProductBatchView:
        self._require_active(actor)
        if actor.role not in {DemoRole.FIELD_CONTROLLER, DemoRole.COORDINATOR}:
            raise OperationsPermissionError(
                "La libération produit exige un contrôleur ou coordinateur autorisé."
            )
        product = self.get_product(product_id)
        if product.quality_status in {"released", "rejected"}:
            raise OperationsConflictError("Une décision qualité finale existe déjà.")
        if not product.quality_tests:
            raise OperationsConflictError(
                "Au moins une analyse ou un contrôle doit précéder la libération."
            )
        release_id = f"RELEASE-{uuid4().hex[:16].upper()}"
        with self.database.session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO product_release_events
                        (id, product_batch_id, status, note, actor_user_id,
                         actor_organization_id, proof_level, correlation_id, created_at)
                    VALUES (:id, :product_id, :status, :note, :actor_user_id,
                            :actor_organization_id, 'P4', :correlation_id, :created_at)
                    """
                ),
                {
                    "id": release_id,
                    "product_id": product_id,
                    "status": data.status,
                    "note": data.note,
                    "actor_user_id": actor.user_id,
                    "actor_organization_id": actor.organization_id,
                    "correlation_id": correlation_id,
                    "created_at": _sql_datetime(_now()),
                },
            )
            session.execute(
                text("UPDATE product_batches SET quality_status = :status WHERE id = :id"),
                {"status": data.status, "id": product_id},
            )
        return self.get_product(product_id)

    def reserve(
        self,
        product_id: str,
        data: ReservationCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> ReservationView:
        self._require_active(actor)
        if actor.role != DemoRole.CLIENT:
            raise OperationsPermissionError("La réservation est réservée au portail client.")
        product = self.get_product(product_id)
        if product.quality_status != "released":
            raise OperationsPermissionError("Un produit non libéré ne peut pas être réservé.")
        if product.unit != data.unit:
            raise OperationsError("L’unité de réservation doit correspondre au lot produit.")
        with self.database.session() as session:
            existing = session.execute(
                text(
                    """
                    SELECT * FROM customer_reservations
                    WHERE customer_organization_id = :organization_id
                      AND idempotency_key = :idempotency_key
                    """
                ),
                {
                    "organization_id": actor.organization_id,
                    "idempotency_key": data.idempotency_key,
                },
            ).mappings().first()
            if existing:
                if (
                    existing["product_batch_id"] != product_id
                    or Decimal(existing["quantity"]) != data.quantity
                    or existing["unit"] != data.unit
                ):
                    raise OperationsConflictError(
                        "Cette clé d’idempotence appartient à une réservation différente."
                    )
                return ReservationView.model_validate(dict(existing))
            _, _, available = self._balance(session, product_id)
            if data.quantity > available:
                raise OperationsConflictError("Stock disponible insuffisant ; stock négatif interdit.")
            reservation_id = f"RES-{uuid4().hex[:16].upper()}"
            created_at = _now()
            session.execute(
                text(
                    """
                    INSERT INTO customer_reservations
                        (id, product_batch_id, customer_organization_id, quantity,
                         unit, status, idempotency_key, actor_user_id,
                         correlation_id, created_at, cancelled_at, delivered_at)
                    VALUES (:id, :product_id, :organization_id, :quantity, :unit,
                            'active', :idempotency_key, :actor_user_id,
                            :correlation_id, :created_at, NULL, NULL)
                    """
                ),
                {
                    "id": reservation_id,
                    "product_id": product_id,
                    "organization_id": actor.organization_id,
                    "quantity": str(data.quantity),
                    "unit": data.unit,
                    "idempotency_key": data.idempotency_key,
                    "actor_user_id": actor.user_id,
                    "correlation_id": correlation_id,
                    "created_at": _sql_datetime(created_at),
                },
            )
            self._insert_movement(
                session,
                product_id=product_id,
                movement_type="reservation",
                quantity=data.quantity,
                unit=data.unit,
                on_hand_delta=Decimal("0"),
                reserved_delta=data.quantity,
                reason="Réservation cliente explicite.",
                reservation_id=reservation_id,
                idempotency_key=f"reservation:{reservation_id}",
                actor=actor,
                proof_level=ProofLevel.P1,
                correlation_id=correlation_id,
            )
            row = session.execute(
                text("SELECT * FROM customer_reservations WHERE id = :id"),
                {"id": reservation_id},
            ).mappings().one()
        return ReservationView.model_validate(dict(row))

    def list_reservations(self, actor: DemoActor) -> list[ReservationView]:
        self._require_active(actor)
        if actor.role == DemoRole.CLIENT:
            clause, params = "WHERE customer_organization_id = :organization_id", {"organization_id": actor.organization_id}
        elif actor.role == DemoRole.UNIT_OPERATOR:
            self._unit_id(actor)
            clause, params = (
                "JOIN product_batches product ON product.id = reservation.product_batch_id "
                "WHERE product.owner_organization_id = :organization_id",
                {"organization_id": actor.organization_id},
            )
        elif actor.role == DemoRole.COORDINATOR:
            clause, params = "", {}
        else:
            return []
        with self.database.session() as session:
            rows = session.execute(
                text(
                    f"SELECT reservation.* FROM customer_reservations reservation "
                    f"{clause} ORDER BY reservation.created_at DESC"
                ),
                params,
            ).mappings().all()
        return [ReservationView.model_validate(dict(row)) for row in rows]

    def cancel_reservation(
        self, reservation_id: str, actor: DemoActor, *, correlation_id: str
    ) -> ReservationView:
        self._require_active(actor)
        with self.database.session() as session:
            row = session.execute(
                text("SELECT * FROM customer_reservations WHERE id = :id"),
                {"id": reservation_id},
            ).mappings().first()
            if row is None:
                raise OperationsError("Réservation introuvable.")
            if actor.role != DemoRole.COORDINATOR and (
                actor.role != DemoRole.CLIENT
                or row["customer_organization_id"] != actor.organization_id
            ):
                raise OperationsPermissionError("Seul le client propriétaire peut annuler cette réservation.")
            if row["status"] == "cancelled":
                return ReservationView.model_validate(dict(row))
            if row["status"] != "active":
                raise OperationsConflictError("Cette réservation ne peut plus être annulée.")
            now = _now()
            session.execute(
                text("UPDATE customer_reservations SET status = 'cancelled', cancelled_at = :now WHERE id = :id"),
                {"now": _sql_datetime(now), "id": reservation_id},
            )
            self._insert_movement(
                session,
                product_id=row["product_batch_id"],
                movement_type="cancellation",
                quantity=Decimal(row["quantity"]),
                unit=row["unit"],
                on_hand_delta=Decimal("0"),
                reserved_delta=-Decimal(row["quantity"]),
                reason="Annulation explicite de la réservation cliente.",
                reservation_id=reservation_id,
                idempotency_key=f"cancellation:{reservation_id}",
                actor=actor,
                proof_level=ProofLevel.P1,
                correlation_id=correlation_id,
            )
            updated = session.execute(
                text("SELECT * FROM customer_reservations WHERE id = :id"), {"id": reservation_id}
            ).mappings().one()
        return ReservationView.model_validate(dict(updated))

    def adjust_inventory(
        self,
        product_id: str,
        data: InventoryAdjustmentCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> ProductBatchView:
        product = self.get_product(product_id)
        if actor.role != DemoRole.COORDINATOR:
            self._unit_id(actor)
            if product.owner_organization_id != actor.organization_id:
                raise OperationsPermissionError("Ce produit appartient à une autre unité.")
        if product.unit != data.unit:
            raise OperationsError("L’unité d’ajustement doit correspondre au produit.")
        with self.database.session() as session:
            existing = session.execute(
                text("SELECT 1 FROM inventory_movements WHERE idempotency_key = :key"),
                {"key": f"adjustment:{actor.organization_id}:{data.idempotency_key}"},
            ).first()
            if existing:
                return self.get_product(product_id)
            on_hand, reserved, _ = self._balance(session, product_id)
            if on_hand + data.quantity_delta < reserved or on_hand + data.quantity_delta < 0:
                raise OperationsConflictError("Cet ajustement créerait un stock négatif.")
            self._insert_movement(
                session,
                product_id=product_id,
                movement_type="adjustment",
                quantity=abs(data.quantity_delta),
                unit=data.unit,
                on_hand_delta=data.quantity_delta,
                reserved_delta=Decimal("0"),
                reason=data.reason,
                reservation_id=None,
                idempotency_key=f"adjustment:{actor.organization_id}:{data.idempotency_key}",
                actor=actor,
                proof_level=ProofLevel.P3,
                correlation_id=correlation_id,
            )
        return self.get_product(product_id)

    def deliver_reservation(
        self, reservation_id: str, actor: DemoActor, *, correlation_id: str
    ) -> ReservationView:
        self._require_active(actor)
        with self.database.session() as session:
            row = session.execute(
                text(
                    """
                    SELECT reservation.*, product.owner_organization_id
                    FROM customer_reservations reservation
                    JOIN product_batches product ON product.id = reservation.product_batch_id
                    WHERE reservation.id = :id
                    """
                ),
                {"id": reservation_id},
            ).mappings().first()
            if row is None:
                raise OperationsError("Réservation introuvable.")
            if actor.role != DemoRole.COORDINATOR:
                self._unit_id(actor)
                if row["owner_organization_id"] != actor.organization_id:
                    raise OperationsPermissionError("Cette réservation concerne une autre unité.")
            if row["status"] != "active":
                raise OperationsConflictError("Seule une réservation active peut être livrée.")
            quantity = Decimal(row["quantity"])
            on_hand, reserved, _ = self._balance(session, row["product_batch_id"])
            if quantity > on_hand or quantity > reserved:
                raise OperationsConflictError("Le registre ne permet pas cette livraison.")
            now = _now()
            session.execute(
                text("UPDATE customer_reservations SET status = 'delivered', delivered_at = :now WHERE id = :id"),
                {"now": _sql_datetime(now), "id": reservation_id},
            )
            self._insert_movement(
                session,
                product_id=row["product_batch_id"],
                movement_type="delivery",
                quantity=quantity,
                unit=row["unit"],
                on_hand_delta=-quantity,
                reserved_delta=-quantity,
                reason="Sortie physique liée à une réservation active.",
                reservation_id=reservation_id,
                idempotency_key=f"delivery:{reservation_id}",
                actor=actor,
                proof_level=ProofLevel.P3,
                correlation_id=correlation_id,
            )
            updated = session.execute(
                text("SELECT * FROM customer_reservations WHERE id = :id"), {"id": reservation_id}
            ).mappings().one()
        return ReservationView.model_validate(dict(updated))

    def list_movements(self, product_id: str, actor: DemoActor) -> list[InventoryMovementView]:
        product = self.get_product(product_id)
        self._require_active(actor)
        if actor.role == DemoRole.UNIT_OPERATOR and product.owner_organization_id != actor.organization_id:
            raise OperationsPermissionError("Ce produit appartient à une autre unité.")
        if actor.role == DemoRole.CLIENT:
            if product.quality_status != "released":
                raise OperationsPermissionError("Produit non publié.")
        elif actor.role not in {DemoRole.UNIT_OPERATOR, DemoRole.FIELD_CONTROLLER, DemoRole.COORDINATOR}:
            raise OperationsPermissionError("Registre d’inventaire non autorisé.")
        with self.database.session() as session:
            rows = session.execute(
                text("SELECT * FROM inventory_movements WHERE product_batch_id = :id ORDER BY created_at, id"),
                {"id": product_id},
            ).mappings().all()
        return [InventoryMovementView.model_validate(dict(row)) for row in rows]

    def build_workspace(self, actor: DemoActor) -> OperationsWorkspace:
        self._require_active(actor)
        accepted = self.list_accepted_lots(actor) if actor.role == DemoRole.UNIT_OPERATOR else []
        transformations = self.list_transformations(actor)
        products = self.list_products(actor)
        reservations = self.list_reservations(actor)
        return OperationsWorkspace(
            actor=actor,
            accepted_lots=accepted,
            transformations=transformations,
            products=products,
            reservations=reservations,
        )

    def provenance_chain(self, product_id: str, actor: DemoActor) -> dict:
        product = self.get_product(product_id)
        self._require_active(actor)
        if actor.role == DemoRole.CLIENT and product.quality_status != "released":
            raise OperationsPermissionError("Produit non publié.")
        if actor.role == DemoRole.UNIT_OPERATOR and product.owner_organization_id != actor.organization_id:
            raise OperationsPermissionError("Ce produit appartient à une autre unité.")
        if actor.role not in {DemoRole.CLIENT, DemoRole.UNIT_OPERATOR, DemoRole.FIELD_CONTROLLER, DemoRole.COORDINATOR}:
            raise OperationsPermissionError("Chaîne de provenance non autorisée.")
        with self.database.session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT declaration.id AS declaration_id,
                           declaration.owner_organization_id,
                           declaration.created_at AS declaration_created_at,
                           lot.id AS lot_id, lot.created_at AS lot_created_at,
                           measurement.id AS measurement_id,
                           measurement.measured_at,
                           collection.id AS collection_id,
                           collection.confirmed_at,
                           input.measured_quantity AS transformation_input_quantity,
                           input.proof_level AS transformation_input_proof
                    FROM transformation_inputs input
                    JOIN lots lot ON lot.id = input.lot_id
                    JOIN waste_declarations declaration ON declaration.id = lot.declaration_id
                    JOIN measurements measurement ON measurement.id = lot.measurement_id
                    LEFT JOIN collections collection
                      ON collection.declaration_id = declaration.id
                     AND collection.processing_unit_id = lot.processing_unit_id
                    WHERE input.transformation_id = :transformation_id
                    ORDER BY lot.id
                    """
                ),
                {"transformation_id": product.transformation_id},
            ).mappings().all()
            declaration_ids = [row["declaration_id"] for row in rows]
            evidence = []
            if declaration_ids:
                placeholders = ",".join(f":d{index}" for index in range(len(declaration_ids)))
                evidence = [
                    dict(item)
                    for item in session.execute(
                        text(
                            f"SELECT id, declaration_id, category, submitted_at FROM evidence WHERE declaration_id IN ({placeholders}) ORDER BY submitted_at, id"
                        ),
                        {f"d{index}": value for index, value in enumerate(declaration_ids)},
                    ).mappings().all()
                ]
            quality = [item.model_dump(mode="json") for item in self._quality_tests(session, product_id)]
            movements = [
                dict(item)
                for item in session.execute(
                    text("SELECT * FROM inventory_movements WHERE product_batch_id = :id ORDER BY created_at, id"),
                    {"id": product_id},
                ).mappings().all()
            ]
            reservations = [
                dict(item)
                for item in session.execute(
                    text("SELECT * FROM customer_reservations WHERE product_batch_id = :id ORDER BY created_at, id"),
                    {"id": product_id},
                ).mappings().all()
            ]
        transformation = self.get_transformation(product.transformation_id)
        return {
            "chain": [
                "declaration", "evidence", "measurement", "collection",
                "input_lot", "transformation", "product_batch", "quality_control",
                "inventory", "reservation",
            ],
            "declarations_to_inputs": [dict(row) for row in rows],
            "evidence": evidence,
            "transformation": transformation.model_dump(mode="json"),
            "product": product.model_dump(mode="json"),
            "quality_controls": quality,
            "inventory_movements": movements,
            "reservations": reservations,
            "proof_notice": "P4 est une libération vérifiée interne ; aucune certification P5 n’est créée.",
        }

    def analytics_dataset(self, actor: DemoActor) -> dict:
        if actor.role != DemoRole.COORDINATOR or actor.membership_status != "active":
            raise OperationsPermissionError("Le jeu analytique interne est réservé au coordinateur.")
        with self.database.session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT transformation.id AS transformation_id,
                           transformation.process, transformation.started_at,
                           transformation.completed_at, transformation.status,
                           transformation.loss_quantity, transformation.loss_unit,
                           transformation.loss_proof_level,
                           input.lot_id, input.measured_quantity AS input_quantity,
                           input.quantity_unit AS input_unit,
                           input.proof_level AS input_proof_level,
                           lot.waste_type_id, lot.status AS input_acceptance,
                           product.id AS product_batch_id, product.category,
                           product.quantity AS output_quantity, product.unit AS output_unit,
                           product.proof_level AS output_proof_level,
                           product.quality_status
                    FROM transformation_runs transformation
                    JOIN transformation_inputs input ON input.transformation_id = transformation.id
                    JOIN lots lot ON lot.id = input.lot_id
                    LEFT JOIN product_batches product ON product.transformation_id = transformation.id
                    ORDER BY transformation.created_at, transformation.id, input.lot_id, product.id
                    """
                )
            ).mappings().all()
        return {
            "schema_version": "transformation-analytics-v1",
            "classification": "jeu analytique interne — aucune validation scientifique",
            "training_authorized": False,
            "external_llm_used": False,
            "rows": [dict(row) for row in rows],
        }
