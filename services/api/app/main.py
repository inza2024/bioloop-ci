from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .catalog import Catalog
from .config import Settings
from .estimation import EstimationEngine
from .evidence import (
    MAX_EVIDENCE_BYTES,
    EvidenceStorage,
    EvidenceValidationError,
)
from .matching import compatible_units
from .models import (
    DeclarationTimeline,
    EvidenceCategory,
    EvidenceLabel,
    EvidenceRecord,
    LotCreate,
    LotDecisionCreate,
    LotDecisionRecord,
    LotRecord,
    MeasurementCreate,
    MeasurementRecord,
    ProofLevel,
    Proposal,
    ProposalCreate,
    Provenance,
    RecalculationCreate,
    RecalculationResult,
    UnitMatch,
    WasteDeclaration,
    WasteDeclarationCreate,
)
from .repository import Repository, RepositoryConflictError
from .routing import propose_route


def correlation_id() -> str:
    return f"CORR-{uuid4().hex[:12].upper()}"


async def read_limited_body(request: Request) -> bytes:
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_EVIDENCE_BYTES:
            raise HTTPException(status_code=413, detail="Le fichier dépasse la limite de 5 Mo.")
    return bytes(content)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    catalog = Catalog(settings.fixtures_dir)
    repository = Repository(settings.db_path)
    evidence_storage = EvidenceStorage(settings.evidence_dir)
    estimator = EstimationEngine(settings.factor_set_path)

    app = FastAPI(
        title="BioLoop CI — API de démonstration",
        version="0.2.0",
        description=(
            "Tranches verticales locales P1, P2 et P3. Les facteurs et toutes "
            "les sorties d'estimation restent des simulations illustratives P0."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Correlation-ID"],
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "mode": "local-demo", "version": app.version}

    @app.get("/api/v1/catalog")
    async def get_catalog() -> dict:
        return {
            "disclaimer": (
                "Tous les producteurs, unités, coordonnées, capacités et "
                "compatibilités de ce catalogue sont fictifs (P0)."
            ),
            "producers": catalog.producers,
            "processing_units": catalog.processing_units,
            "waste_types": catalog.waste_types,
            "evidence_levels": [
                EvidenceLabel(provenance=Provenance.SIMULATED, proof_level=ProofLevel.P0, label="Simulé"),
                EvidenceLabel(provenance=Provenance.DECLARED, proof_level=ProofLevel.P1, label="Déclaré"),
                EvidenceLabel(provenance=Provenance.DOCUMENTED, proof_level=ProofLevel.P2, label="Documenté"),
                EvidenceLabel(provenance=Provenance.MEASURED, proof_level=ProofLevel.P3, label="Mesuré"),
                EvidenceLabel(provenance=Provenance.VERIFIED, proof_level=ProofLevel.P4, label="Vérifié"),
                EvidenceLabel(provenance=Provenance.CERTIFIED, proof_level=ProofLevel.P5, label="Certifié"),
            ],
        }

    @app.get("/api/v1/declarations", response_model=list[WasteDeclaration])
    async def list_declarations() -> list[WasteDeclaration]:
        return repository.list_declarations()

    @app.post(
        "/api/v1/declarations",
        response_model=WasteDeclaration,
        status_code=201,
    )
    async def create_declaration(data: WasteDeclarationCreate) -> WasteDeclaration:
        producer = catalog.producer(data.producer_id)
        if producer is None:
            raise HTTPException(status_code=404, detail="Producteur fictif inconnu.")
        if catalog.waste_type(data.waste_type_id) is None:
            raise HTTPException(status_code=422, detail="Type de déchet inconnu.")
        declaration = repository.create_declaration(data, producer)
        repository.append_audit_event(
            correlation_id=correlation_id(),
            declaration_id=declaration.id,
            event_type="declaration.created",
            object_type="waste_declaration",
            object_id=declaration.id,
            payload={
                "proof_level": declaration.proof_level.value,
                "provenance": declaration.provenance.value,
            },
        )
        return declaration

    def require_declaration(declaration_id: str) -> WasteDeclaration:
        declaration = repository.get_declaration(declaration_id)
        if declaration is None:
            raise HTTPException(status_code=404, detail="Déclaration introuvable.")
        return declaration

    def require_measurement(measurement_id: str) -> MeasurementRecord:
        measurement = repository.get_measurement(measurement_id)
        if measurement is None:
            raise HTTPException(status_code=404, detail="Mesure introuvable.")
        return measurement

    def require_lot(lot_id: str) -> LotRecord:
        lot = repository.get_lot(lot_id)
        if lot is None:
            raise HTTPException(status_code=404, detail="Lot introuvable.")
        return lot

    def require_compatible_unit(
        declaration: WasteDeclaration,
        processing_unit_id: str,
        quantity_kg: Decimal | None = None,
    ):
        unit = catalog.processing_unit(processing_unit_id)
        if unit is None:
            raise HTTPException(status_code=404, detail="Unité fictive inconnue.")
        candidate = (
            declaration.model_copy(update={"quantity_kg": quantity_kg})
            if quantity_kg is not None
            else declaration
        )
        eligible_ids = {
            match.processing_unit_id for match in compatible_units(candidate, catalog)
        }
        if unit.id not in eligible_ids:
            raise HTTPException(
                status_code=422,
                detail="Unité incompatible avec le type ou la capacité simulée.",
            )
        return unit

    @app.get(
        "/api/v1/declarations/{declaration_id}/matches",
        response_model=list[UnitMatch],
    )
    async def get_matches(declaration_id: str) -> list[UnitMatch]:
        return compatible_units(require_declaration(declaration_id), catalog)

    @app.post(
        "/api/v1/declarations/{declaration_id}/proposal",
        response_model=Proposal,
    )
    async def create_proposal(declaration_id: str, data: ProposalCreate) -> Proposal:
        declaration = require_declaration(declaration_id)
        unit = require_compatible_unit(declaration, data.processing_unit_id)
        estimate = estimator.calculate(declaration, unit.id)
        route = propose_route(declaration, unit, estimate.calculation_hash)
        corr_id = correlation_id()
        repository.save_estimate_run(
            estimate=estimate,
            processing_unit_id=unit.id,
            input_snapshot={
                "quantity_kg": str(declaration.quantity_kg),
                "waste_type_id": declaration.waste_type_id,
                "processing_unit_id": unit.id,
                "input_provenance": Provenance.DECLARED.value,
                "input_proof_level": ProofLevel.P1.value,
                "source_measurement_id": None,
            },
            output_snapshot={
                "scenarios": [
                    {"key": scenario.key, "value": str(scenario.value)}
                    for scenario in estimate.scenarios
                ],
                "route_total_straight_line_km": str(route.total_straight_line_km),
                "proof_level": ProofLevel.P0.value,
            },
        )
        repository.append_audit_event(
            correlation_id=corr_id,
            declaration_id=declaration.id,
            event_type="proposal.generated",
            object_type="estimate_run",
            object_id=estimate.id,
            payload={
                "calculation_hash": estimate.calculation_hash,
                "factor_set_version": estimate.factor_set_version,
                "input_proof_level": ProofLevel.P1.value,
                "output_proof_level": ProofLevel.P0.value,
                "route_id": route.id,
                "status": route.status,
            },
        )
        return Proposal(
            correlation_id=corr_id,
            declaration=declaration,
            selected_unit=unit,
            estimate=estimate,
            route=route,
        )

    @app.post(
        "/api/v1/declarations/{declaration_id}/evidence",
        response_model=EvidenceRecord,
        status_code=201,
    )
    async def create_evidence(
        declaration_id: str,
        request: Request,
        category: EvidenceCategory = Query(...),
        original_filename: str = Query(..., min_length=1, max_length=180),
        captured_at: datetime | None = Query(default=None),
        note: str = Query(default="", max_length=500),
    ) -> EvidenceRecord:
        require_declaration(declaration_id)
        if captured_at and (captured_at.tzinfo is None or captured_at.utcoffset() is None):
            raise HTTPException(
                status_code=422,
                detail="La date de capture déclarée doit inclure un fuseau horaire.",
            )
        content = await read_limited_body(request)
        try:
            stored = evidence_storage.store(
                category=category,
                original_filename=original_filename,
                media_type=request.headers.get("content-type", ""),
                content=content,
                captured_at=captured_at,
                note=note,
            )
        except EvidenceValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            evidence = repository.create_evidence(declaration_id, stored)
        except Exception:
            evidence_storage.discard(stored.storage_name)
            raise
        repository.append_audit_event(
            correlation_id=correlation_id(),
            declaration_id=declaration_id,
            event_type="evidence.created",
            object_type="evidence",
            object_id=evidence.id,
            payload={
                "category": evidence.category,
                "media_type": evidence.media_type,
                "proof_level": ProofLevel.P2.value,
                "sha256": evidence.sha256,
                "size_bytes": evidence.size_bytes,
            },
        )
        return evidence

    @app.get(
        "/api/v1/declarations/{declaration_id}/evidence",
        response_model=list[EvidenceRecord],
    )
    async def list_evidence(declaration_id: str) -> list[EvidenceRecord]:
        require_declaration(declaration_id)
        return repository.list_evidence(declaration_id)

    @app.post(
        "/api/v1/declarations/{declaration_id}/measurements",
        response_model=MeasurementRecord,
        status_code=201,
    )
    async def create_measurement(
        declaration_id: str, data: MeasurementCreate
    ) -> MeasurementRecord:
        require_declaration(declaration_id)
        if data.evidence_id:
            evidence = repository.get_evidence(data.evidence_id)
            if evidence is None or evidence.declaration_id != declaration_id:
                raise HTTPException(
                    status_code=422,
                    detail="La preuve P2 doit appartenir à la même déclaration.",
                )
        if data.supersedes_measurement_id:
            previous = repository.get_measurement(data.supersedes_measurement_id)
            if previous is None or previous.declaration_id != declaration_id:
                raise HTTPException(
                    status_code=422,
                    detail="La mesure corrigée doit appartenir à la même déclaration.",
                )
        measurement = repository.create_measurement(declaration_id, data)
        repository.append_audit_event(
            correlation_id=correlation_id(),
            declaration_id=declaration_id,
            event_type="measurement.recorded",
            object_type="measurement",
            object_id=measurement.id,
            payload={
                "method": measurement.method,
                "proof_level": ProofLevel.P3.value,
                "quantity_unit": measurement.unit,
                "supersedes_measurement_id": measurement.supersedes_measurement_id,
            },
        )
        return measurement

    @app.get(
        "/api/v1/declarations/{declaration_id}/measurements",
        response_model=list[MeasurementRecord],
    )
    async def list_measurements(declaration_id: str) -> list[MeasurementRecord]:
        require_declaration(declaration_id)
        return repository.list_measurements(declaration_id)

    @app.post(
        "/api/v1/declarations/{declaration_id}/lots",
        response_model=LotRecord,
        status_code=201,
    )
    async def create_lot(declaration_id: str, data: LotCreate) -> LotRecord:
        declaration = require_declaration(declaration_id)
        measurement = require_measurement(data.measurement_id)
        if measurement.declaration_id != declaration_id:
            raise HTTPException(
                status_code=422,
                detail="La mesure P3 doit appartenir à la déclaration du lot.",
            )
        require_compatible_unit(
            declaration, data.processing_unit_id, measurement.quantity_kg
        )
        evidence_ids = list(dict.fromkeys(data.evidence_ids))
        for evidence_id in evidence_ids:
            evidence = repository.get_evidence(evidence_id)
            if evidence is None or evidence.declaration_id != declaration_id:
                raise HTTPException(
                    status_code=422,
                    detail="Toutes les preuves du lot doivent appartenir à la déclaration.",
                )
        lot = repository.create_lot(
            declaration=declaration,
            measurement=measurement,
            processing_unit_id=data.processing_unit_id,
            evidence_ids=evidence_ids,
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            declaration_id=declaration_id,
            event_type="lot.created",
            object_type="waste_lot",
            object_id=lot.id,
            payload={
                "measurement_id": measurement.id,
                "processing_unit_id": lot.processing_unit_id,
                "input_proof_level": ProofLevel.P3.value,
                "quantity_unit": lot.quantity_unit,
            },
        )
        return lot

    @app.get("/api/v1/lots/{lot_id}", response_model=LotRecord)
    async def get_lot(lot_id: str) -> LotRecord:
        return require_lot(lot_id)

    @app.post(
        "/api/v1/lots/{lot_id}/decision",
        response_model=LotDecisionRecord,
        status_code=201,
    )
    async def decide_lot(
        lot_id: str, data: LotDecisionCreate
    ) -> LotDecisionRecord:
        lot = require_lot(lot_id)
        try:
            decision = repository.record_lot_decision(lot, data)
        except RepositoryConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        repository.append_audit_event(
            correlation_id=correlation_id(),
            declaration_id=lot.declaration_id,
            event_type=f"lot.{decision.decision}",
            object_type="waste_lot",
            object_id=lot.id,
            payload={
                "actor_authenticated": False,
                "actor_label": decision.actor_label,
                "processing_unit_id": lot.processing_unit_id,
                "proof_level": ProofLevel.P1.value,
            },
        )
        return decision

    @app.post(
        "/api/v1/declarations/{declaration_id}/recalculations",
        response_model=RecalculationResult,
        status_code=201,
    )
    async def recalculate_from_measurement(
        declaration_id: str, data: RecalculationCreate
    ) -> RecalculationResult:
        declaration = require_declaration(declaration_id)
        measurement = require_measurement(data.measurement_id)
        if measurement.declaration_id != declaration_id:
            raise HTTPException(
                status_code=422,
                detail="La mesure source doit appartenir à la déclaration.",
            )
        unit = require_compatible_unit(
            declaration, data.processing_unit_id, measurement.quantity_kg
        )
        previous = repository.latest_estimate_run(declaration_id, unit.id)
        if previous is None:
            raise HTTPException(
                status_code=409,
                detail="Créez d'abord la proposition fondée sur la masse déclarée.",
            )
        if repository.recalculation_exists(measurement.id, unit.id):
            raise HTTPException(
                status_code=409,
                detail="Cette mesure possède déjà un recalcul pour cette unité.",
            )
        estimate = estimator.calculate(
            declaration,
            unit.id,
            input_quantity_kg=measurement.quantity_kg,
            input_provenance=Provenance.MEASURED,
            input_proof_level=ProofLevel.P3,
            source_measurement_id=measurement.id,
            supersedes_estimate_run_id=previous.id,
        )
        repository.save_estimate_run(
            estimate=estimate,
            processing_unit_id=unit.id,
            input_snapshot={
                "quantity_kg": str(measurement.quantity_kg),
                "waste_type_id": declaration.waste_type_id,
                "processing_unit_id": unit.id,
                "input_provenance": Provenance.MEASURED.value,
                "input_proof_level": ProofLevel.P3.value,
                "source_measurement_id": measurement.id,
            },
            output_snapshot={
                "scenarios": [
                    {"key": scenario.key, "value": str(scenario.value)}
                    for scenario in estimate.scenarios
                ],
                "proof_level": ProofLevel.P0.value,
            },
        )
        lineage = repository.link_estimates(
            parent_estimate_run_id=previous.id,
            child_estimate_run_id=estimate.id,
            source_measurement_id=measurement.id,
        )
        corr_id = correlation_id()
        repository.append_audit_event(
            correlation_id=corr_id,
            declaration_id=declaration_id,
            event_type="estimate.recalculated_from_measurement",
            object_type="estimate_run",
            object_id=estimate.id,
            payload={
                "calculation_hash": estimate.calculation_hash,
                "factor_set_version": estimate.factor_set_version,
                "input_proof_level": ProofLevel.P3.value,
                "output_proof_level": ProofLevel.P0.value,
                "parent_estimate_run_id": previous.id,
                "source_measurement_id": measurement.id,
            },
        )
        return RecalculationResult(
            correlation_id=corr_id,
            previous_estimate=previous,
            estimate=estimate,
            lineage=lineage,
        )

    @app.get(
        "/api/v1/declarations/{declaration_id}/timeline",
        response_model=DeclarationTimeline,
    )
    async def get_timeline(declaration_id: str) -> DeclarationTimeline:
        declaration = require_declaration(declaration_id)
        return DeclarationTimeline(
            declaration=declaration,
            evidence=repository.list_evidence(declaration_id),
            measurements=repository.list_measurements(declaration_id),
            lots=repository.list_lots(declaration_id),
            estimate_runs=repository.list_estimate_runs(declaration_id),
            estimate_lineage=repository.list_estimate_lineage(declaration_id),
            audit_events=repository.list_audit_events(declaration_id),
        )

    return app


app = create_app()
