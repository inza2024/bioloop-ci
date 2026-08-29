from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .catalog import Catalog
from .config import Settings
from .estimation import EstimationEngine
from .matching import compatible_units
from .models import (
    EvidenceLabel,
    ProofLevel,
    Proposal,
    ProposalCreate,
    Provenance,
    UnitMatch,
    WasteDeclaration,
    WasteDeclarationCreate,
)
from .repository import Repository
from .routing import propose_route


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    catalog = Catalog(settings.fixtures_dir)
    repository = Repository(settings.db_path)
    estimator = EstimationEngine(settings.factor_set_path)

    app = FastAPI(
        title="BioLoop CI — API de démonstration",
        version="0.1.0",
        description=(
            "Première tranche verticale locale. Rendements et logistique sont "
            "des simulations illustratives P0, sans validation scientifique."
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
        correlation_id = f"CORR-{uuid4().hex[:12].upper()}"
        repository.append_audit_event(
            correlation_id=correlation_id,
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
        unit = catalog.processing_unit(data.processing_unit_id)
        if unit is None:
            raise HTTPException(status_code=404, detail="Unité fictive inconnue.")
        eligible_ids = {
            match.processing_unit_id
            for match in compatible_units(declaration, catalog)
        }
        if unit.id not in eligible_ids:
            raise HTTPException(
                status_code=422,
                detail="Unité incompatible avec le type ou la capacité simulée.",
            )
        estimate = estimator.calculate(declaration, unit.id)
        route = propose_route(declaration, unit, estimate.calculation_hash)
        correlation_id = f"CORR-{uuid4().hex[:12].upper()}"
        repository.save_estimate_run(
            estimate=estimate,
            processing_unit_id=unit.id,
            input_snapshot={
                "quantity_kg": str(declaration.quantity_kg),
                "waste_type_id": declaration.waste_type_id,
                "processing_unit_id": unit.id,
            },
            output_snapshot={
                "scenarios": [
                    {"key": scenario.key, "value": str(scenario.value)}
                    for scenario in estimate.scenarios
                ],
                "route_total_straight_line_km": str(route.total_straight_line_km),
            },
        )
        repository.append_audit_event(
            correlation_id=correlation_id,
            event_type="proposal.generated",
            object_type="estimate_run",
            object_id=estimate.id,
            payload={
                "calculation_hash": estimate.calculation_hash,
                "factor_set_version": estimate.factor_set_version,
                "route_id": route.id,
                "status": route.status,
            },
        )
        return Proposal(
            correlation_id=correlation_id,
            declaration=declaration,
            selected_unit=unit,
            estimate=estimate,
            route=route,
        )

    return app


app = create_app()
