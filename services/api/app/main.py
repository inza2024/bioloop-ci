from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .catalog import Catalog
from .collaboration import AuthorizationError, CollaborationService, MODE_LABEL
from .config import Settings
from .estimation import EstimationEngine
from .evidence import (
    MAX_EVIDENCE_BYTES,
    EvidenceStorage,
    EvidenceValidationError,
)
from .matching import compatible_units
from .forecasting import DeterministicDeclarationForecastService
from .identity import DEFAULT_DEMO_USER_ID, IdentityDirectory, IdentityError
from .models import (
    AuditEventRecord,
    CollectionConfirmCreate,
    CollectionRecord,
    DeclarationTimeline,
    DemoActor,
    DemoActorCatalog,
    DemoRole,
    DemoWorkspace,
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
    VerificationCreate,
    VerificationRecord,
    WasteDeclaration,
    WasteDeclarationCreate,
)
from .repository import Repository, RepositoryConflictError
from .routing import propose_route


DeclarationPath = Annotated[str, Path(pattern=r"^DECL-[A-F0-9]{12}$")]
LotPath = Annotated[str, Path(pattern=r"^LOT-[A-F0-9]{12}$")]
CollectionPath = Annotated[str, Path(pattern=r"^COLL-[A-F0-9]{12}$")]


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
    identities = IdentityDirectory(settings.fixtures_dir / "demo_identities.json")
    repository.seed_demo_identities(
        identities.organizations, identities.users, identities.memberships
    )
    repository.backfill_declaration_owners(
        {
            organization.site_id: organization.id
            for organization in identities.organizations
            if organization.site_type == "producer" and organization.site_id
        }
    )
    collaboration = CollaborationService(
        repository=repository,
        catalog=catalog,
        identities=identities,
        forecast_service=DeterministicDeclarationForecastService(),
    )

    app = FastAPI(
        title="BioLoop CI — API de démonstration",
        version="0.3.0",
        description=(
            "Démonstrateur local multi-acteurs. L'identité choisie n'est pas une "
            "authentification de production. Les facteurs, itinéraires et projections "
            "restent des simulations illustratives P0."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Correlation-ID", "X-Demo-User-ID"],
    )

    def resolve_actor(user_id: str) -> DemoActor:
        try:
            return identities.actor(user_id)
        except IdentityError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    async def current_actor(
        x_demo_user_id: Annotated[str | None, Header()] = None,
    ) -> DemoActor:
        # Compatibilité des deux premières tranches : sans en-tête, le parcours
        # historique agit comme coordinateur de démonstration.
        return resolve_actor(x_demo_user_id or DEFAULT_DEMO_USER_ID)

    async def explicit_demo_actor(
        x_demo_user_id: Annotated[str | None, Header()] = None,
    ) -> DemoActor:
        if x_demo_user_id is None:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Sélectionnez explicitement une identité de démonstration via "
                    "X-Demo-User-ID. Ce mécanisme n'est pas une authentification."
                ),
            )
        return resolve_actor(x_demo_user_id)

    def enforce(action) -> None:
        try:
            action()
        except AuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "mode": "local-demo", "version": app.version}

    @app.get("/api/v1/demo/actors", response_model=DemoActorCatalog)
    async def get_demo_actors() -> DemoActorCatalog:
        return DemoActorCatalog(mode_label=MODE_LABEL, actors=identities.actors)

    @app.get("/api/v1/demo/workspace", response_model=DemoWorkspace)
    async def get_demo_workspace(
        as_of: date = Query(default_factory=date.today),
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> DemoWorkspace:
        try:
            return collaboration.build_workspace(actor, as_of=as_of)
        except AuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/api/v1/demo/notifications")
    async def get_demo_notifications(
        actor: DemoActor = Depends(explicit_demo_actor),
    ):
        return repository.list_notifications(actor)

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
    async def list_declarations(
        actor: DemoActor = Depends(current_actor),
    ) -> list[WasteDeclaration]:
        if actor.role == DemoRole.COORDINATOR:
            return repository.list_declarations()
        if actor.role == DemoRole.PRODUCER:
            return repository.list_declarations_for_organization(actor.organization_id)
        raise HTTPException(
            status_code=403,
            detail="Utilisez le portail associé à ce rôle pour consulter ses objets autorisés.",
        )

    @app.post(
        "/api/v1/declarations",
        response_model=WasteDeclaration,
        status_code=201,
    )
    async def create_declaration(
        data: WasteDeclarationCreate,
        actor: DemoActor = Depends(current_actor),
    ) -> WasteDeclaration:
        producer = catalog.producer(data.producer_id)
        if producer is None:
            raise HTTPException(status_code=404, detail="Producteur fictif inconnu.")
        if catalog.waste_type(data.waste_type_id) is None:
            raise HTTPException(status_code=422, detail="Type de déchet inconnu.")
        try:
            owner_organization_id = collaboration.require_create_declaration(
                actor, data.producer_id
            )
        except AuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        declaration = repository.create_declaration(
            data, producer, owner_organization_id=owner_organization_id
        )
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
            actor=actor,
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
    async def get_matches(
        declaration_id: DeclarationPath,
        actor: DemoActor = Depends(current_actor),
    ) -> list[UnitMatch]:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_producer_operation(actor, declaration))
        return compatible_units(declaration, catalog)

    @app.post(
        "/api/v1/declarations/{declaration_id}/proposal",
        response_model=Proposal,
    )
    async def create_proposal(
        declaration_id: DeclarationPath,
        data: ProposalCreate,
        actor: DemoActor = Depends(current_actor),
    ) -> Proposal:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_producer_operation(actor, declaration))
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
            actor=actor,
        )
        collaboration.register_proposal(
            declaration=declaration,
            route=route,
            processing_unit_id=unit.id,
            actor=actor,
            correlation_id=corr_id,
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
        declaration_id: DeclarationPath,
        request: Request,
        category: EvidenceCategory = Query(...),
        original_filename: str = Query(..., min_length=1, max_length=180),
        captured_at: datetime | None = Query(default=None),
        note: str = Query(default="", max_length=500),
        actor: DemoActor = Depends(current_actor),
    ) -> EvidenceRecord:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_evidence_create(actor, declaration))
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
            actor=actor,
        )
        return evidence

    @app.get(
        "/api/v1/declarations/{declaration_id}/evidence",
        response_model=list[EvidenceRecord],
    )
    async def list_evidence(
        declaration_id: DeclarationPath,
        actor: DemoActor = Depends(current_actor),
    ) -> list[EvidenceRecord]:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_declaration_read(actor, declaration))
        return repository.list_evidence(declaration_id)

    @app.post(
        "/api/v1/declarations/{declaration_id}/measurements",
        response_model=MeasurementRecord,
        status_code=201,
    )
    async def create_measurement(
        declaration_id: DeclarationPath,
        data: MeasurementCreate,
        actor: DemoActor = Depends(current_actor),
    ) -> MeasurementRecord:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_measurement_create(actor, declaration))
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
            actor=actor,
        )
        return measurement

    @app.get(
        "/api/v1/declarations/{declaration_id}/measurements",
        response_model=list[MeasurementRecord],
    )
    async def list_measurements(
        declaration_id: DeclarationPath,
        actor: DemoActor = Depends(current_actor),
    ) -> list[MeasurementRecord]:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_declaration_read(actor, declaration))
        return repository.list_measurements(declaration_id)

    @app.post(
        "/api/v1/declarations/{declaration_id}/lots",
        response_model=LotRecord,
        status_code=201,
    )
    async def create_lot(
        declaration_id: DeclarationPath,
        data: LotCreate,
        actor: DemoActor = Depends(current_actor),
    ) -> LotRecord:
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
        enforce(
            lambda: collaboration.require_lot_create(
                actor, declaration, data.processing_unit_id
            )
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
            actor=actor,
        )
        collaboration.notify_lot_created(lot, actor)
        return lot

    @app.get("/api/v1/lots/{lot_id}", response_model=LotRecord)
    async def get_lot(
        lot_id: LotPath,
        actor: DemoActor = Depends(current_actor),
    ) -> LotRecord:
        lot = require_lot(lot_id)
        enforce(lambda: collaboration.require_lot_read(actor, lot))
        return lot

    @app.post(
        "/api/v1/lots/{lot_id}/decision",
        response_model=LotDecisionRecord,
        status_code=201,
    )
    async def decide_lot(
        lot_id: LotPath,
        data: LotDecisionCreate,
        actor: DemoActor = Depends(current_actor),
    ) -> LotDecisionRecord:
        lot = require_lot(lot_id)
        enforce(lambda: collaboration.require_lot_decision(actor, lot))
        try:
            decision = repository.record_lot_decision(lot, data, actor)
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
            actor=actor,
        )
        decided_lot = require_lot(lot.id)
        collaboration.notify_lot_decision(decided_lot, actor)
        return decision

    @app.post(
        "/api/v1/declarations/{declaration_id}/recalculations",
        response_model=RecalculationResult,
        status_code=201,
    )
    async def recalculate_from_measurement(
        declaration_id: DeclarationPath,
        data: RecalculationCreate,
        actor: DemoActor = Depends(current_actor),
    ) -> RecalculationResult:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_declaration_read(actor, declaration))
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
            actor=actor,
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
    async def get_timeline(
        declaration_id: DeclarationPath,
        actor: DemoActor = Depends(current_actor),
    ) -> DeclarationTimeline:
        declaration = require_declaration(declaration_id)
        enforce(lambda: collaboration.require_declaration_read(actor, declaration))
        return DeclarationTimeline(
            declaration=declaration,
            evidence=repository.list_evidence(declaration_id),
            measurements=repository.list_measurements(declaration_id),
            lots=repository.list_lots(declaration_id),
            estimate_runs=repository.list_estimate_runs(declaration_id),
            estimate_lineage=repository.list_estimate_lineage(declaration_id),
            audit_events=repository.list_audit_events(declaration_id),
        )

    @app.post(
        "/api/v1/demo/collections/{collection_id}/confirm",
        response_model=CollectionRecord,
    )
    async def confirm_collection(
        collection_id: CollectionPath,
        data: CollectionConfirmCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> CollectionRecord:
        collection = repository.get_collection(collection_id)
        if collection is None:
            raise HTTPException(status_code=404, detail="Collecte introuvable.")
        enforce(lambda: collaboration.require_collection_confirm(actor, collection))
        evidence = repository.get_evidence(data.evidence_id)
        measurement = repository.get_measurement(data.measurement_id)
        if (
            evidence is None
            or evidence.declaration_id != collection.declaration_id
            or measurement is None
            or measurement.declaration_id != collection.declaration_id
            or measurement.evidence_id != evidence.id
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "La preuve P2 et la mesure P3 liée doivent appartenir à la "
                    "déclaration de cette collecte."
                ),
            )
        try:
            confirmed = repository.confirm_collection(
                collection,
                evidence_id=evidence.id,
                measurement_id=measurement.id,
                actor=actor,
            )
        except RepositoryConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        corr_id = correlation_id()
        repository.append_audit_event(
            correlation_id=corr_id,
            declaration_id=collection.declaration_id,
            event_type="collection.confirmed",
            object_type="collection",
            object_id=collection.id,
            payload={
                "evidence_id": evidence.id,
                "evidence_proof_level": ProofLevel.P2.value,
                "measurement_id": measurement.id,
                "measurement_proof_level": ProofLevel.P3.value,
            },
            actor=actor,
        )
        return confirmed

    @app.post(
        "/api/v1/demo/verifications",
        response_model=VerificationRecord,
        status_code=201,
    )
    async def create_verification(
        data: VerificationCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> VerificationRecord:
        enforce(lambda: collaboration.require_controller(actor))
        lot = require_lot(data.subject_id)
        existing = repository.verification_by_idempotency_key(data.idempotency_key)
        if existing is not None:
            if (
                existing.subject_id != data.subject_id
                or existing.outcome != data.outcome
                or existing.note != data.note
                or existing.actor_user_id != actor.user_id
                or existing.actor_organization_id != actor.organization_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Cette clé d'idempotence appartient à un contrôle différent ; "
                        "l'historique ne peut pas être modifié silencieusement."
                    ),
                )
            return existing
        verification = repository.create_verification(data, actor)
        repository.append_audit_event(
            correlation_id=correlation_id(),
            declaration_id=lot.declaration_id,
            event_type="verification.recorded",
            object_type=data.subject_type,
            object_id=data.subject_id,
            payload={
                "outcome": data.outcome,
                "proof_level": ProofLevel.P4.value,
                "idempotency_key": data.idempotency_key,
            },
            actor=actor,
        )
        return verification

    @app.get("/api/v1/demo/audit", response_model=list[AuditEventRecord])
    async def get_demo_audit(
        actor_user_id: str | None = Query(
            default=None, pattern=r"^USER-[A-Z0-9-]{3,40}$"
        ),
        organization_id: str | None = Query(
            default=None, pattern=r"^ORG-[A-Z0-9-]{3,40}$"
        ),
        object_type: str | None = Query(
            default=None, pattern=r"^[a-z][a-z0-9_.-]{1,59}$"
        ),
        correlation_id_filter: str | None = Query(
            default=None,
            alias="correlation_id",
            pattern=r"^CORR-[A-F0-9]{12}$",
        ),
        limit: int = Query(default=100, ge=1, le=500),
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> list[AuditEventRecord]:
        enforce(lambda: collaboration.require_coordinator(actor))
        return repository.filter_audit_events(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            object_type=object_type,
            correlation_id=correlation_id_filter,
            limit=limit,
        )

    return app


app = create_app()
