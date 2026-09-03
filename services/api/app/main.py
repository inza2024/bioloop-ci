from __future__ import annotations

import re
from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .catalog import Catalog
from .auth import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    AuthConflictError,
    AuthContext,
    AuthError,
    AuthPermissionError,
    AuthRateLimitError,
    AuthService,
    LoginCreate,
    RegistrationCreate,
    csrf_matches,
    new_csrf_token,
)
from .administration import (
    AdminActionView,
    AdministrationConflictError,
    AdministrationError,
    AdministrationPermissionError,
    AdministrationService,
    InvitationAcceptResult,
    InvitationCreate,
    InvitationView,
    MembershipDecisionCreate,
    PendingMembership,
    RevocationCreate,
    SessionView,
)
from .collaboration import AuthorizationError, CollaborationService, MODE_LABEL
from .config import Settings
from .database import Database, run_migrations
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
from .operations import (
    InventoryAdjustmentCreate,
    InventoryMovementView,
    OperationsConflictError,
    OperationsError,
    OperationsPermissionError,
    OperationsService,
    OperationsWorkspace,
    ProductBatchView,
    ProductOutputsCreate,
    ProductReleaseCreate,
    QualityTestCreate,
    QualityTestView,
    ReservationCreate,
    ReservationView,
    TransformationCreate,
    TransformationStatusCreate,
    TransformationView,
)


DeclarationPath = Annotated[str, Path(pattern=r"^DECL-[A-F0-9]{12}$")]
LotPath = Annotated[str, Path(pattern=r"^LOT-[A-F0-9]{12}$")]
CollectionPath = Annotated[str, Path(pattern=r"^COLL-[A-F0-9]{12}$")]
MembershipPath = Annotated[str, Path(pattern=r"^PMEM-[A-F0-9]{16}$")]
SessionPath = Annotated[str, Path(pattern=r"^PSESS-[A-F0-9]{16}$")]
TransformationPath = Annotated[str, Path(pattern=r"^TRUN-[A-F0-9]{16}$")]
ProductPath = Annotated[str, Path(pattern=r"^PRODLOT-[A-F0-9]{16}$")]
ReservationPath = Annotated[str, Path(pattern=r"^RES-[A-F0-9]{16}$")]
InvitationTokenPath = Annotated[str, Path(min_length=32, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]
CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,99}$")
REQUEST_CORRELATION_ID: ContextVar[str | None] = ContextVar(
    "bioloop_request_correlation_id", default=None
)


def correlation_id() -> str:
    return REQUEST_CORRELATION_ID.get() or f"CORR-{uuid4().hex[:12].upper()}"


async def read_limited_body(request: Request) -> bytes:
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_EVIDENCE_BYTES:
            raise HTTPException(status_code=413, detail="Le fichier dépasse la limite de 5 Mo.")
    return bytes(content)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    catalog = Catalog(settings.fixtures_dir, profile=settings.synthetic_profile)
    repository = Repository(settings.db_path)
    run_migrations(settings.resolved_database_url)
    database = Database(settings.resolved_database_url)
    auth = AuthService(database, session_ttl_seconds=settings.session_ttl_seconds)
    administration = AdministrationService(database)
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
    operations = OperationsService(database)

    app = FastAPI(
        title="BioLoop CI — API de démonstration",
        version="0.5.0",
        description=(
            "Démonstrateur local multi-acteurs. L'identité choisie n'est pas une "
            "authentification de production. Les facteurs, itinéraires et projections "
            "restent des simulations illustratives P0. Les sorties de transformation "
            "sont exclusivement des mesures explicitement enregistrées."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=[
            "Content-Type",
            "X-Correlation-ID",
            "X-CSRF-Token",
            "X-Demo-User-ID",
        ],
    )

    @app.middleware("http")
    async def security_and_correlation_middleware(request: Request, call_next):
        supplied = request.headers.get("X-Correlation-ID", "")
        request.state.correlation_id = (
            supplied
            if CORRELATION_PATTERN.fullmatch(supplied)
            else f"CORR-{uuid4().hex[:12].upper()}"
        )

        def harden(response: Response) -> Response:
            response.headers["X-Correlation-ID"] = request.state.correlation_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "same-origin"
            response.headers["Permissions-Policy"] = (
                "camera=(), microphone=(), geolocation=()"
            )
            if request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store"
            return response

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_EVIDENCE_BYTES + 16_384:
                    return harden(
                        Response(status_code=413, content="Requête trop volumineuse.")
                    )
            except ValueError:
                return harden(
                    Response(status_code=400, content="Longueur de requête invalide.")
                )
        if (
            request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and request.cookies.get(SESSION_COOKIE)
            and not csrf_matches(
                request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
            )
        ):
            return harden(Response(status_code=403, content="Protection CSRF requise."))
        context_token = REQUEST_CORRELATION_ID.set(request.state.correlation_id)
        try:
            response = await call_next(request)
        finally:
            REQUEST_CORRELATION_ID.reset(context_token)
        return harden(response)

    def resolve_actor(user_id: str) -> DemoActor:
        try:
            return identities.actor(user_id)
        except IdentityError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    async def current_actor(
        request: Request,
        x_demo_user_id: Annotated[str | None, Header()] = None,
    ) -> DemoActor:
        context = auth.resolve(request.cookies.get(SESSION_COOKIE))
        if context is not None:
            return context.actor
        if x_demo_user_id and settings.demo_identities_enabled:
            return resolve_actor(x_demo_user_id)
        # Compatibility mode is local and explicitly disableable.
        if settings.demo_identities_enabled:
            return resolve_actor(DEFAULT_DEMO_USER_ID)
        raise HTTPException(status_code=401, detail="Authentification requise.")

    async def explicit_demo_actor(
        request: Request,
        x_demo_user_id: Annotated[str | None, Header()] = None,
    ) -> DemoActor:
        context = auth.resolve(request.cookies.get(SESSION_COOKIE))
        if context is not None:
            return context.actor
        if not settings.demo_identities_enabled:
            raise HTTPException(status_code=404, detail="Mode démonstration désactivé.")
        if x_demo_user_id is None:
            raise HTTPException(
                status_code=401,
                detail=(
                    "Sélectionnez explicitement une identité de démonstration via "
                    "X-Demo-User-ID. Ce mécanisme n'est pas une authentification."
                ),
            )
        return resolve_actor(x_demo_user_id)

    async def current_auth_context(request: Request) -> AuthContext:
        context = auth.resolve(request.cookies.get(SESSION_COOKIE))
        if context is None:
            raise HTTPException(status_code=401, detail="Session invalide ou expirée.")
        return context

    def require_csrf(request: Request) -> None:
        if not csrf_matches(
            request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
        ):
            raise HTTPException(status_code=403, detail="Protection CSRF requise.")
        origin = request.headers.get("origin")
        if origin and origin != settings.web_origin:
            raise HTTPException(status_code=403, detail="Origine non autorisée.")

    def set_session_cookie(response: Response, token: str) -> None:
        response.set_cookie(
            SESSION_COOKIE,
            token,
            max_age=settings.session_ttl_seconds,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )

    def auth_audit(
        request: Request,
        *,
        event_type: str,
        object_id: str,
        actor: DemoActor | None = None,
        payload: dict | None = None,
    ) -> None:
        repository.append_audit_event(
            correlation_id=request.state.correlation_id,
            event_type=event_type,
            object_type="pilot_identity",
            object_id=object_id,
            payload=payload or {},
            actor=actor,
        )

    def enforce(action) -> None:
        try:
            action()
        except AuthorizationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "mode": "local-demo", "version": app.version}

    @app.get("/api/v1/auth/csrf")
    async def issue_csrf(response: Response) -> dict[str, str]:
        token = new_csrf_token()
        response.set_cookie(
            CSRF_COOKIE,
            token,
            max_age=86_400,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="lax",
            path="/",
        )
        return {"csrf_token": token}

    @app.post("/api/v1/auth/register", response_model=AuthContext, status_code=201)
    async def register(
        data: RegistrationCreate, request: Request, response: Response
    ) -> AuthContext:
        require_csrf(request)
        try:
            grant = auth.register(data)
        except AuthPermissionError as exc:
            auth_audit(request, event_type="auth.registration_denied", object_id="SELF-SERVICE")
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except AuthConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        set_session_cookie(response, grant.token)
        auth_audit(
            request,
            event_type="auth.registered",
            object_id=grant.context.user.id,
            actor=grant.context.actor,
            payload={
                "role": grant.context.active_membership.role.value,
                "membership_status": grant.context.active_membership.status,
            },
        )
        return grant.context

    @app.post("/api/v1/auth/login", response_model=AuthContext)
    async def login(
        data: LoginCreate, request: Request, response: Response
    ) -> AuthContext:
        require_csrf(request)
        try:
            grant = auth.login(
                data, client_ip=request.client.host if request.client else "unknown"
            )
        except AuthRateLimitError as exc:
            auth_audit(request, event_type="auth.rate_limited", object_id="LOGIN")
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except AuthError as exc:
            auth_audit(request, event_type="auth.login_failed", object_id="LOGIN")
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        set_session_cookie(response, grant.token)
        auth_audit(
            request,
            event_type="auth.login_succeeded",
            object_id=grant.context.user.id,
            actor=grant.context.actor,
        )
        return grant.context

    @app.get("/api/v1/auth/me", response_model=AuthContext)
    async def auth_me(
        context: AuthContext = Depends(current_auth_context),
    ) -> AuthContext:
        return context

    @app.post("/api/v1/auth/logout")
    async def logout(
        request: Request,
        response: Response,
        context: AuthContext = Depends(current_auth_context),
    ) -> dict[str, str]:
        auth.logout(request.cookies.get(SESSION_COOKIE))
        response.delete_cookie(SESSION_COOKIE, path="/")
        auth_audit(
            request,
            event_type="auth.logged_out",
            object_id=context.user.id,
            actor=context.actor,
        )
        return {"status": "logged_out"}

    @app.post(
        "/api/v1/auth/memberships/{membership_id}/activate",
        response_model=AuthContext,
    )
    async def activate_membership(
        membership_id: MembershipPath,
        request: Request,
        context: AuthContext = Depends(current_auth_context),
    ) -> AuthContext:
        try:
            updated = auth.switch_membership(
                request.cookies.get(SESSION_COOKIE, ""), membership_id
            )
        except AuthPermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        auth_audit(
            request,
            event_type="auth.membership_activated",
            object_id=membership_id,
            actor=updated.actor,
            payload={"previous_membership_id": context.active_membership.id},
        )
        return updated

    @app.get("/api/v1/auth/portal/{role}")
    async def authenticated_portal(
        role: DemoRole,
        context: AuthContext = Depends(current_auth_context),
    ) -> dict:
        membership = context.active_membership
        if role != membership.role:
            raise HTTPException(status_code=403, detail="Portail non autorisé pour ce rôle.")
        declarations = (
            repository.list_declarations_for_organization(membership.organization_id)
            if role == DemoRole.PRODUCER and membership.status == "active"
            else []
        )
        return {
            "context": context,
            "notifications": repository.list_notifications(context.actor),
            "declarations": declarations,
            "counters": {
                "declarations": len(declarations),
                "notifications": len(repository.list_notifications(context.actor)),
            },
            "proof_summary": (
                "Les nouvelles déclarations sont P1 ; les catalogues et projections restent P0."
            ),
            "next_action": (
                "Validation de l’organisation requise avant toute action métier."
                if membership.status == "pending"
                else "Utilisez les actions autorisées pour votre organisation active."
            ),
        }

    def admin_call(action):
        try:
            return action()
        except AdministrationPermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except AdministrationConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except AdministrationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    def operations_call(action):
        try:
            return action()
        except OperationsPermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except OperationsConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OperationsError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get(
        "/api/v1/admin/memberships/pending",
        response_model=list[PendingMembership],
    )
    async def pending_memberships(
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> list[PendingMembership]:
        return admin_call(lambda: administration.list_pending_memberships(actor))

    @app.post("/api/v1/admin/memberships/{membership_id}/decision")
    async def decide_membership(
        membership_id: MembershipPath,
        data: MembershipDecisionCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> dict:
        admin_call(
            lambda: administration.decide_membership(
                membership_id,
                data,
                actor,
                correlation_id=correlation_id(),
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="admin.membership_decided",
            object_type="pilot_membership",
            object_id=membership_id,
            payload={
                "decision": data.decision,
                "reason_provided": bool(data.reason),
                "processing_unit_id": data.processing_unit_id,
            },
            actor=actor,
        )
        return {
            "membership_id": membership_id,
            "decision": data.decision,
            "status": "active" if data.decision == "approved" else "refused",
        }

    @app.post(
        "/api/v1/admin/invitations",
        response_model=InvitationView,
        status_code=201,
    )
    async def create_invitation(
        data: InvitationCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> InvitationView:
        invitation = admin_call(
            lambda: administration.create_invitation(
                data, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="admin.invitation_created",
            object_type="pilot_role_invitation",
            object_id=invitation.id,
            payload={
                "role": invitation.role.value,
                "organization_id": invitation.organization_id,
                "expires_at": invitation.expires_at.isoformat(),
                "token_stored_as_hash": True,
                "delivery": invitation.delivery,
            },
            actor=actor,
        )
        return invitation

    @app.post(
        "/api/v1/auth/invitations/{token}/accept",
        response_model=InvitationAcceptResult,
    )
    async def accept_invitation(
        token: InvitationTokenPath,
        request: Request,
        context: AuthContext = Depends(current_auth_context),
    ) -> InvitationAcceptResult:
        require_csrf(request)
        accepted = admin_call(
            lambda: administration.accept_invitation(
                token,
                actor=context.actor,
                email=context.user.email,
                correlation_id=correlation_id(),
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="auth.invitation_accepted",
            object_type="pilot_membership",
            object_id=accepted.membership_id,
            payload={
                "organization_id": accepted.organization_id,
                "role": accepted.role.value,
            },
            actor=context.actor,
        )
        return accepted

    @app.get("/api/v1/admin/sessions", response_model=list[SessionView])
    async def active_sessions(
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> list[SessionView]:
        return admin_call(lambda: administration.list_sessions(actor))

    @app.post("/api/v1/admin/memberships/{membership_id}/revoke")
    async def revoke_membership(
        membership_id: MembershipPath,
        data: RevocationCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> dict[str, str]:
        admin_call(
            lambda: administration.revoke_membership(
                membership_id,
                actor,
                reason=data.reason,
                correlation_id=correlation_id(),
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="admin.membership_revoked",
            object_type="pilot_membership",
            object_id=membership_id,
            payload={"reason_provided": True},
            actor=actor,
        )
        return {"status": "revoked"}

    @app.post("/api/v1/admin/sessions/{session_id}/revoke")
    async def revoke_session(
        session_id: SessionPath,
        data: RevocationCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> dict[str, str]:
        admin_call(
            lambda: administration.revoke_session(
                session_id,
                actor,
                reason=data.reason,
                correlation_id=correlation_id(),
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="admin.session_revoked",
            object_type="pilot_session",
            object_id=session_id,
            payload={"reason_provided": True},
            actor=actor,
        )
        return {"status": "revoked"}

    @app.get("/api/v1/admin/history", response_model=list[AdminActionView])
    async def admin_history(
        limit: int = Query(default=100, ge=1, le=500),
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> list[AdminActionView]:
        return admin_call(lambda: administration.list_history(actor, limit=limit))

    @app.get("/api/v1/operations/workspace", response_model=OperationsWorkspace)
    async def operations_workspace(
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> OperationsWorkspace:
        return operations_call(lambda: operations.build_workspace(actor))

    @app.post(
        "/api/v1/transformations",
        response_model=TransformationView,
        status_code=201,
    )
    async def create_transformation(
        data: TransformationCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> TransformationView:
        item = operations_call(
            lambda: operations.create_transformation(
                data, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="transformation.created",
            object_type="transformation_run",
            object_id=item.id,
            payload={
                "processing_unit_id": item.processing_unit_id,
                "input_lot_ids": [entry.lot_id for entry in item.inputs],
                "input_proof_level": ProofLevel.P3.value,
                "scientific_derivation": False,
            },
            actor=actor,
        )
        return item

    @app.post(
        "/api/v1/transformations/{transformation_id}/status",
        response_model=TransformationView,
    )
    async def update_transformation_status(
        transformation_id: TransformationPath,
        data: TransformationStatusCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> TransformationView:
        item = operations_call(
            lambda: operations.update_transformation_status(
                transformation_id, data, actor
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type=f"transformation.{item.status}",
            object_type="transformation_run",
            object_id=item.id,
            payload={
                "status": item.status,
                "loss_proof_level": item.loss_proof_level.value if item.loss_proof_level else None,
            },
            actor=actor,
        )
        return item

    @app.post(
        "/api/v1/transformations/{transformation_id}/outputs",
        response_model=list[ProductBatchView],
        status_code=201,
    )
    async def create_product_outputs(
        transformation_id: TransformationPath,
        data: ProductOutputsCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> list[ProductBatchView]:
        products = operations_call(
            lambda: operations.create_outputs(
                transformation_id, data, actor, correlation_id=correlation_id()
            )
        )
        for product in products:
            repository.append_audit_event(
                correlation_id=correlation_id(),
                event_type="product.measured_output_recorded",
                object_type="product_batch",
                object_id=product.id,
                payload={
                    "transformation_id": transformation_id,
                    "category": product.category,
                    "quantity": str(product.quantity),
                    "unit": product.unit,
                    "proof_level": ProofLevel.P3.value,
                    "derived_from_illustrative_uri": False,
                },
                actor=actor,
            )
        return products

    @app.post(
        "/api/v1/products/{product_id}/quality-tests",
        response_model=QualityTestView,
        status_code=201,
    )
    async def create_quality_test(
        product_id: ProductPath,
        data: QualityTestCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> QualityTestView:
        quality = operations_call(
            lambda: operations.add_quality_test(
                product_id, data, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="product.quality_test_recorded",
            object_type="product_batch",
            object_id=product_id,
            payload={
                "quality_test_id": quality.id,
                "parameter": quality.parameter,
                "proof_level": quality.proof_level.value,
            },
            actor=actor,
        )
        return quality

    @app.post(
        "/api/v1/products/{product_id}/release",
        response_model=ProductBatchView,
    )
    async def release_product(
        product_id: ProductPath,
        data: ProductReleaseCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> ProductBatchView:
        product = operations_call(
            lambda: operations.release_product(
                product_id, data, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type=f"product.{data.status}",
            object_type="product_batch",
            object_id=product_id,
            payload={
                "quality_status": data.status,
                "proof_level": ProofLevel.P4.value,
                "certified": False,
            },
            actor=actor,
        )
        return product

    @app.get("/api/v1/products", response_model=list[ProductBatchView])
    async def list_products(
        category: str | None = Query(default=None, max_length=50),
        location: str | None = Query(default=None, max_length=120),
        proof_level: ProofLevel | None = Query(default=None),
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> list[ProductBatchView]:
        products = operations_call(lambda: operations.list_products(actor))
        return [
            item
            for item in products
            if (not category or item.category == category)
            and (not location or location.casefold() in item.location.casefold())
            and (not proof_level or item.proof_level == proof_level)
        ]

    @app.post(
        "/api/v1/products/{product_id}/reservations",
        response_model=ReservationView,
        status_code=201,
    )
    async def create_reservation(
        product_id: ProductPath,
        data: ReservationCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> ReservationView:
        reservation = operations_call(
            lambda: operations.reserve(
                product_id, data, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="inventory.reserved",
            object_type="customer_reservation",
            object_id=reservation.id,
            payload={
                "product_batch_id": product_id,
                "quantity": str(reservation.quantity),
                "unit": reservation.unit,
            },
            actor=actor,
        )
        return reservation

    @app.post(
        "/api/v1/reservations/{reservation_id}/cancel",
        response_model=ReservationView,
    )
    async def cancel_reservation(
        reservation_id: ReservationPath,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> ReservationView:
        reservation = operations_call(
            lambda: operations.cancel_reservation(
                reservation_id, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="inventory.reservation_cancelled",
            object_type="customer_reservation",
            object_id=reservation.id,
            payload={"product_batch_id": reservation.product_batch_id},
            actor=actor,
        )
        return reservation

    @app.post(
        "/api/v1/reservations/{reservation_id}/deliver",
        response_model=ReservationView,
    )
    async def deliver_reservation(
        reservation_id: ReservationPath,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> ReservationView:
        reservation = operations_call(
            lambda: operations.deliver_reservation(
                reservation_id, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="inventory.delivered",
            object_type="customer_reservation",
            object_id=reservation.id,
            payload={"product_batch_id": reservation.product_batch_id},
            actor=actor,
        )
        return reservation

    @app.post(
        "/api/v1/products/{product_id}/inventory-adjustments",
        response_model=ProductBatchView,
    )
    async def adjust_inventory(
        product_id: ProductPath,
        data: InventoryAdjustmentCreate,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> ProductBatchView:
        product = operations_call(
            lambda: operations.adjust_inventory(
                product_id, data, actor, correlation_id=correlation_id()
            )
        )
        repository.append_audit_event(
            correlation_id=correlation_id(),
            event_type="inventory.adjusted",
            object_type="product_batch",
            object_id=product_id,
            payload={
                "quantity_delta": str(data.quantity_delta),
                "unit": data.unit,
                "reason_provided": True,
            },
            actor=actor,
        )
        return product

    @app.get(
        "/api/v1/products/{product_id}/inventory-movements",
        response_model=list[InventoryMovementView],
    )
    async def inventory_movements(
        product_id: ProductPath,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> list[InventoryMovementView]:
        return operations_call(lambda: operations.list_movements(product_id, actor))

    @app.get("/api/v1/products/{product_id}/provenance")
    async def product_provenance(
        product_id: ProductPath,
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> dict:
        return operations_call(lambda: operations.provenance_chain(product_id, actor))

    @app.get("/api/v1/analytics/transformation-dataset")
    async def transformation_analytics_dataset(
        actor: DemoActor = Depends(explicit_demo_actor),
    ) -> dict:
        return operations_call(lambda: operations.analytics_dataset(actor))

    @app.get("/api/v1/demo/actors", response_model=DemoActorCatalog)
    async def get_demo_actors() -> DemoActorCatalog:
        if not settings.demo_identities_enabled:
            raise HTTPException(status_code=404, detail="Mode démonstration désactivé.")
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
            "synthetic_profile": catalog.profile,
            "synthetic_data": catalog.synthetic_dataset.summary(),
            "evidence_levels": [
                EvidenceLabel(provenance=Provenance.SIMULATED, proof_level=ProofLevel.P0, label="Simulé"),
                EvidenceLabel(provenance=Provenance.DECLARED, proof_level=ProofLevel.P1, label="Déclaré"),
                EvidenceLabel(provenance=Provenance.DOCUMENTED, proof_level=ProofLevel.P2, label="Documenté"),
                EvidenceLabel(provenance=Provenance.MEASURED, proof_level=ProofLevel.P3, label="Mesuré"),
                EvidenceLabel(provenance=Provenance.VERIFIED, proof_level=ProofLevel.P4, label="Vérifié"),
                EvidenceLabel(provenance=Provenance.CERTIFIED, proof_level=ProofLevel.P5, label="Certifié"),
            ],
        }

    @app.get("/api/v1/pilot/synthetic-data")
    async def get_synthetic_data(
        context: AuthContext = Depends(current_auth_context),
    ) -> dict:
        dataset = catalog.synthetic_dataset
        return {
            **dataset.summary(),
            "availability": dataset.availability,
            "logistics": dataset.logistics,
            "operational_history": dataset.operational_history,
            "clients": dataset.clients,
            "transformations": dataset.transformations,
            "products": dataset.products,
            "quality_tests": dataset.quality_tests,
            "inventory_movements": dataset.inventory_movements,
            "reservations": dataset.reservations,
            "accessed_by_organization_id": context.active_membership.organization_id,
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
        if data.client_idempotency_key:
            existing = repository.declaration_by_idempotency_key(
                owner_organization_id, data.client_idempotency_key
            )
            if existing is not None:
                return existing
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
