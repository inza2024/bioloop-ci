from __future__ import annotations

from typing import Protocol

from .models import DemoActor, WasteDeclaration, WasteDeclarationCreate


class DeclarationRepository(Protocol):
    """Boundary used to migrate declarations away from the legacy SQLite adapter."""

    def create_declaration(
        self,
        data: WasteDeclarationCreate,
        producer,
        owner_organization_id: str | None = None,
    ) -> WasteDeclaration: ...

    def get_declaration(self, declaration_id: str) -> WasteDeclaration | None: ...

    def list_declarations_for_organization(
        self, organization_id: str
    ) -> list[WasteDeclaration]: ...

    def declaration_by_idempotency_key(
        self, owner_organization_id: str | None, key: str
    ) -> WasteDeclaration | None: ...


class AuditRepository(Protocol):
    def append_audit_event(
        self,
        *,
        correlation_id: str,
        event_type: str,
        object_type: str,
        object_id: str,
        payload: dict,
        declaration_id: str | None = None,
        actor: DemoActor | None = None,
    ) -> None: ...


class RepositoryUnitOfWork(DeclarationRepository, AuditRepository, Protocol):
    """Minimal cross-cutting port; SQLAlchemy adapters can replace modules gradually."""
