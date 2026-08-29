from __future__ import annotations

from datetime import date

from .catalog import Catalog
from .forecasting import ForecastService
from .identity import IdentityDirectory
from .models import (
    CollectionRecord,
    DemoActor,
    DemoRole,
    DemoWorkspace,
    IncomingLotView,
    LogisticsCollectionView,
    PendingControlView,
    ProducerDeclarationView,
    RoutePlan,
    WasteDeclaration,
)
from .repository import Repository


MODE_LABEL = "mode démonstration — aucune authentification de production"


class AuthorizationError(PermissionError):
    pass


class CollaborationService:
    def __init__(
        self,
        *,
        repository: Repository,
        catalog: Catalog,
        identities: IdentityDirectory,
        forecast_service: ForecastService,
    ) -> None:
        self.repository = repository
        self.catalog = catalog
        self.identities = identities
        self.forecast_service = forecast_service

    @staticmethod
    def _is_coordinator(actor: DemoActor) -> bool:
        return actor.role == DemoRole.COORDINATOR

    def declaration_owner_id(self, declaration: WasteDeclaration) -> str | None:
        if declaration.owner_organization_id:
            return declaration.owner_organization_id
        organization = self.identities.organization_for_site(
            "producer", declaration.producer_id
        )
        return organization.id if organization else None

    def require_create_declaration(
        self, actor: DemoActor, producer_id: str
    ) -> str | None:
        if self._is_coordinator(actor):
            organization = self.identities.organization_for_site(
                "producer", producer_id
            )
            return organization.id if organization else None
        organization = self.identities.organization(actor.organization_id)
        if (
            actor.role != DemoRole.PRODUCER
            or organization is None
            or organization.site_type != "producer"
            or organization.site_id != producer_id
        ):
            raise AuthorizationError(
                "Un producteur ne peut déclarer que pour le site de sa propre organisation."
            )
        return actor.organization_id

    def require_declaration_read(
        self, actor: DemoActor, declaration: WasteDeclaration
    ) -> None:
        if self._is_coordinator(actor) or actor.role == DemoRole.FIELD_CONTROLLER:
            return
        owner_id = self.declaration_owner_id(declaration)
        if actor.role == DemoRole.PRODUCER and owner_id == actor.organization_id:
            return
        collection = self.repository.collection_for_declaration(declaration.id)
        if (
            actor.role == DemoRole.LOGISTICIAN
            and collection
            and collection.logistician_organization_id == actor.organization_id
        ):
            return
        organization = self.identities.organization(actor.organization_id)
        if (
            actor.role == DemoRole.UNIT_OPERATOR
            and organization
            and collection
            and organization.site_id == collection.processing_unit_id
        ):
            return
        raise AuthorizationError("Cette déclaration privée appartient à une autre organisation.")

    def require_producer_operation(
        self, actor: DemoActor, declaration: WasteDeclaration
    ) -> None:
        if self._is_coordinator(actor):
            return
        if (
            actor.role != DemoRole.PRODUCER
            or self.declaration_owner_id(declaration) != actor.organization_id
        ):
            raise AuthorizationError(
                "Cette opération est réservée au producteur propriétaire."
            )

    def require_evidence_create(
        self, actor: DemoActor, declaration: WasteDeclaration
    ) -> None:
        if self._is_coordinator(actor):
            return
        if (
            actor.role == DemoRole.PRODUCER
            and self.declaration_owner_id(declaration) == actor.organization_id
        ):
            return
        collection = self.repository.collection_for_declaration(declaration.id)
        if (
            actor.role == DemoRole.LOGISTICIAN
            and collection
            and collection.logistician_organization_id == actor.organization_id
        ):
            return
        raise AuthorizationError(
            "Seul le producteur propriétaire ou le logisticien assigné peut joindre cette preuve."
        )

    def require_measurement_create(
        self, actor: DemoActor, declaration: WasteDeclaration
    ) -> None:
        if self._is_coordinator(actor):
            return
        collection = self.repository.collection_for_declaration(declaration.id)
        if (
            actor.role == DemoRole.LOGISTICIAN
            and collection
            and collection.logistician_organization_id == actor.organization_id
        ):
            return
        raise AuthorizationError(
            "La pesée P3 est réservée au logisticien assigné dans ce parcours."
        )

    def require_lot_create(
        self, actor: DemoActor, declaration: WasteDeclaration, unit_id: str
    ) -> None:
        if self._is_coordinator(actor):
            return
        collection = self.repository.collection_for_declaration(
            declaration.id, unit_id
        )
        if (
            actor.role != DemoRole.LOGISTICIAN
            or collection is None
            or collection.logistician_organization_id != actor.organization_id
            or collection.status != "collected"
        ):
            raise AuthorizationError(
                "Le lot ne peut être créé que par le logisticien assigné après confirmation de collecte."
            )

    def require_collection_confirm(
        self, actor: DemoActor, collection: CollectionRecord
    ) -> None:
        if (
            actor.role != DemoRole.LOGISTICIAN
            or collection.logistician_organization_id != actor.organization_id
        ):
            raise AuthorizationError(
                "Cette collecte n’est pas assignée à l’organisation logistique active."
            )

    def require_lot_read(self, actor: DemoActor, lot) -> None:
        declaration = self.repository.get_declaration(lot.declaration_id)
        assert declaration is not None
        self.require_declaration_read(actor, declaration)

    def require_lot_decision(self, actor: DemoActor, lot) -> None:
        if self._is_coordinator(actor):
            return
        organization = self.identities.organization(actor.organization_id)
        if (
            actor.role != DemoRole.UNIT_OPERATOR
            or organization is None
            or organization.site_type != "processing_unit"
            or organization.site_id != lot.processing_unit_id
        ):
            raise AuthorizationError(
                "Seul l’opérateur de l’unité destinataire peut accepter ou refuser ce lot."
            )

    @staticmethod
    def require_controller(actor: DemoActor) -> None:
        if actor.role != DemoRole.FIELD_CONTROLLER:
            raise AuthorizationError(
                "Une vérification P4 exige le rôle contrôleur terrain."
            )

    @staticmethod
    def require_coordinator(actor: DemoActor) -> None:
        if actor.role != DemoRole.COORDINATOR:
            raise AuthorizationError(
                "Cette vue transversale est réservée au coordinateur BioLoop."
            )

    def register_proposal(
        self,
        *,
        declaration: WasteDeclaration,
        route: RoutePlan,
        processing_unit_id: str,
        actor: DemoActor,
        correlation_id: str,
    ) -> CollectionRecord:
        logistics = self.identities.organization_for_role(DemoRole.LOGISTICIAN)
        if logistics is None:
            raise RuntimeError("Organisation logistique de démonstration absente.")
        collection = self.repository.create_collection_assignment(
            declaration=declaration,
            route=route,
            processing_unit_id=processing_unit_id,
            logistician_organization_id=logistics.id,
        )
        owner_id = self.declaration_owner_id(declaration)
        if owner_id:
            self.repository.create_notification(
                organization_id=owner_id,
                target_role=DemoRole.PRODUCER,
                event_type="proposal.available",
                subject_type="waste_declaration",
                subject_id=declaration.id,
                message="Une unité compatible et une collecte illustrative sont proposées.",
                dedup_key=f"proposal:{route.id}:producer:{owner_id}",
            )
        self.repository.create_notification(
            organization_id=logistics.id,
            target_role=DemoRole.LOGISTICIAN,
            event_type="collection.assigned",
            subject_type="collection",
            subject_id=collection.id,
            message=(
                f"Collecte illustrative assignée pour {declaration.producer_name} — "
                "validation humaine requise."
            ),
            dedup_key=f"collection:{collection.id}:assigned:{logistics.id}",
        )
        self.repository.append_audit_event(
            correlation_id=correlation_id,
            declaration_id=declaration.id,
            event_type="collection.assigned",
            object_type="collection",
            object_id=collection.id,
            payload={
                "route_id": route.id,
                "logistician_organization_id": logistics.id,
                "distance_classification": "géodésique illustrative P0",
                "human_validation_required": True,
            },
            actor=actor,
        )
        return collection

    def notify_lot_created(self, lot, actor: DemoActor) -> None:
        unit_org = self.identities.organization_for_site(
            "processing_unit", lot.processing_unit_id
        )
        controller_org = self.identities.organization_for_role(
            DemoRole.FIELD_CONTROLLER
        )
        if unit_org:
            self.repository.create_notification(
                organization_id=unit_org.id,
                target_role=DemoRole.UNIT_OPERATOR,
                event_type="lot.incoming",
                subject_type="waste_lot",
                subject_id=lot.id,
                message=f"Lot entrant {lot.id} — {lot.measured_quantity_kg} kg sur base P3.",
                dedup_key=f"lot:{lot.id}:incoming:{unit_org.id}",
            )
        if controller_org:
            self.repository.create_notification(
                organization_id=controller_org.id,
                target_role=DemoRole.FIELD_CONTROLLER,
                event_type="control.required",
                subject_type="waste_lot",
                subject_id=lot.id,
                message=f"Contrôle terrain requis pour le lot {lot.id}.",
                dedup_key=f"lot:{lot.id}:control:{controller_org.id}",
            )

    def notify_lot_decision(self, lot, actor: DemoActor) -> None:
        declaration = self.repository.get_declaration(lot.declaration_id)
        assert declaration is not None
        owner_id = self.declaration_owner_id(declaration)
        collection = self.repository.collection_for_declaration(declaration.id)
        coordinator = self.identities.organization_for_role(DemoRole.COORDINATOR)
        targets = {
            item
            for item in (
                owner_id,
                collection.logistician_organization_id if collection else None,
                coordinator.id if coordinator else None,
            )
            if item
        }
        for organization_id in targets:
            self.repository.create_notification(
                organization_id=organization_id,
                target_role=None,
                event_type="lot.decision_recorded",
                subject_type="waste_lot",
                subject_id=lot.id,
                message=f"Décision {lot.status} enregistrée pour le lot {lot.id}.",
                dedup_key=f"lot:{lot.id}:decision:{lot.status}:{organization_id}",
            )

    def build_workspace(self, actor: DemoActor, *, as_of: date) -> DemoWorkspace:
        workspace = DemoWorkspace(
            actor=actor,
            mode_label=MODE_LABEL,
            permissions=self.identities.permissions(actor),
            notifications=self.repository.list_notifications(actor),
        )
        if actor.role == DemoRole.PRODUCER:
            workspace.producer_declarations = self._producer_views(
                self.repository.list_declarations_for_organization(
                    actor.organization_id
                )
            )
        elif actor.role == DemoRole.LOGISTICIAN:
            workspace.logistics_collections = self._logistics_views(
                self.repository.list_collections_for_logistician(
                    actor.organization_id
                )
            )
        elif actor.role == DemoRole.UNIT_OPERATOR:
            unit_id = self._actor_unit_id(actor)
            workspace.incoming_lots = self._incoming_lot_views(unit_id)
            workspace.projections = [self._forecast(unit_id, as_of=as_of)]
        elif actor.role == DemoRole.FIELD_CONTROLLER:
            workspace.pending_controls = self._pending_controls()
        elif actor.role == DemoRole.COORDINATOR:
            workspace.coordinator_counts = self.repository.coordinator_counts()
            workspace.producer_declarations = self._producer_views(
                self.repository.list_declarations()
            )
            workspace.logistics_collections = self._logistics_views(
                self.repository.list_collections()
            )
            workspace.incoming_lots = self._all_lot_views()
            workspace.pending_controls = self._pending_controls()
            workspace.audit_events = self.repository.filter_audit_events(limit=100)
        else:
            workspace.product_empty_state = (
                "Aucun produit ou stock qualifié n’est encore représenté. "
                "La transformation, la qualification produit et les disponibilités "
                "mesurées seront traitées dans une tranche ultérieure."
            )
        return workspace

    def _producer_views(
        self, declarations: list[WasteDeclaration]
    ) -> list[ProducerDeclarationView]:
        views: list[ProducerDeclarationView] = []
        for declaration in declarations:
            collection = self.repository.collection_for_declaration(declaration.id)
            lots = self.repository.list_lots(declaration.id)
            lot = lots[-1] if lots else None
            if lot and lot.status in {"accepted", "refused"}:
                next_action = f"Décision unité : {lot.status}."
            elif lot:
                next_action = "Attendre la décision de l’unité."
            elif collection and collection.status == "collected":
                next_action = "Lot à constituer depuis la mesure P3."
            elif collection:
                next_action = "Collecte assignée ; ajouter si besoin une preuve P2."
            else:
                next_action = "Sélectionner une unité et générer une proposition."
            views.append(
                ProducerDeclarationView(
                    declaration=declaration,
                    proposed_unit_id=(
                        collection.processing_unit_id if collection else None
                    ),
                    collection_status=collection.status if collection else None,
                    lot_status=lot.status if lot else None,
                    next_action=next_action,
                )
            )
        return views

    def _logistics_views(
        self, collections: list[CollectionRecord]
    ) -> list[LogisticsCollectionView]:
        views: list[LogisticsCollectionView] = []
        for collection in collections:
            declaration = self.repository.get_declaration(collection.declaration_id)
            unit = self.catalog.processing_unit(collection.processing_unit_id)
            if declaration is None or unit is None:
                continue
            waste = self.catalog.waste_type(declaration.waste_type_id)
            views.append(
                LogisticsCollectionView(
                    collection=collection,
                    producer_name=declaration.producer_name,
                    waste_type_name=waste.name if waste else declaration.waste_type_id,
                    processing_unit_name=unit.name,
                    available_capacity_kg=(
                        unit.daily_capacity_kg - unit.reserved_capacity_kg
                    ),
                )
            )
        return views

    def _actor_unit_id(self, actor: DemoActor) -> str:
        organization = self.identities.organization(actor.organization_id)
        if organization is None or organization.site_type != "processing_unit":
            raise AuthorizationError("Aucune unité n’est liée à cet acteur.")
        assert organization.site_id is not None
        return organization.site_id

    def _incoming_lot_views(self, unit_id: str) -> list[IncomingLotView]:
        unit = self.catalog.processing_unit(unit_id)
        if unit is None:
            return []
        views: list[IncomingLotView] = []
        for lot in self.repository.list_lots_for_unit(unit_id):
            declaration = self.repository.get_declaration(lot.declaration_id)
            if declaration is None:
                continue
            waste = self.catalog.waste_type(lot.waste_type_id)
            views.append(
                IncomingLotView(
                    lot=lot,
                    producer_name=declaration.producer_name,
                    waste_type_name=waste.name if waste else lot.waste_type_id,
                    compatibility=(
                        lot.waste_type_id in unit.accepted_waste_type_ids
                        and lot.measured_quantity_kg
                        <= unit.daily_capacity_kg - unit.reserved_capacity_kg
                    ),
                    available_capacity_kg=(
                        unit.daily_capacity_kg - unit.reserved_capacity_kg
                    ),
                )
            )
        return views

    def _pending_controls(self) -> list[PendingControlView]:
        controls: list[PendingControlView] = []
        for lot in self.repository.list_all_lots():
            verification = self.repository.latest_verification("waste_lot", lot.id)
            if verification is not None:
                continue
            declaration = self.repository.get_declaration(lot.declaration_id)
            if declaration:
                controls.append(
                    PendingControlView(
                        lot=lot,
                        producer_name=declaration.producer_name,
                    )
                )
        return controls

    def _all_lot_views(self) -> list[IncomingLotView]:
        views: list[IncomingLotView] = []
        for lot in self.repository.list_all_lots():
            unit = self.catalog.processing_unit(lot.processing_unit_id)
            declaration = self.repository.get_declaration(lot.declaration_id)
            if unit is None or declaration is None:
                continue
            waste = self.catalog.waste_type(lot.waste_type_id)
            views.append(
                IncomingLotView(
                    lot=lot,
                    producer_name=declaration.producer_name,
                    waste_type_name=waste.name if waste else lot.waste_type_id,
                    compatibility=(
                        lot.waste_type_id in unit.accepted_waste_type_ids
                        and lot.measured_quantity_kg
                        <= unit.daily_capacity_kg - unit.reserved_capacity_kg
                    ),
                    available_capacity_kg=(
                        unit.daily_capacity_kg - unit.reserved_capacity_kg
                    ),
                )
            )
        return views

    def _forecast(self, unit_id: str, *, as_of: date):
        declarations: dict[str, WasteDeclaration] = {}
        for collection in self.repository.list_collections_for_unit(unit_id):
            declaration = self.repository.get_declaration(collection.declaration_id)
            if declaration:
                declarations[declaration.id] = declaration
        inputs = [
            (declaration, self.repository.latest_measurement(declaration.id))
            for declaration in declarations.values()
        ]
        return self.forecast_service.project_unit_intake(
            unit_id, inputs, as_of=as_of
        )
