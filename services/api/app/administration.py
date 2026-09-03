from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text

from .auth import EMAIL_PATTERN
from .database import Database
from .models import DemoActor, DemoRole


class AdministrationError(ValueError):
    pass


class AdministrationConflictError(AdministrationError):
    pass


class AdministrationPermissionError(AdministrationError):
    pass


class MembershipDecisionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    decision: Literal["approved", "refused"]
    reason: str = Field(default="", max_length=500)
    processing_unit_id: str | None = Field(
        default=None, pattern=r"^UNIT-[0-9]{3}$"
    )

    @model_validator(mode="after")
    def refusal_requires_reason(self) -> "MembershipDecisionCreate":
        if self.decision == "refused" and len(self.reason) < 3:
            raise ValueError("Un motif de refus d’au moins trois caractères est requis.")
        return self


class PendingMembership(BaseModel):
    id: str
    user_id: str
    display_name: str
    organization_id: str
    organization_name: str
    organization_kind: str
    role: DemoRole
    status: Literal["pending"]
    created_at: datetime


class InvitationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: str = Field(min_length=5, max_length=254)
    role: Literal["field_controller", "bioloop_coordinator"]
    organization_id: str | None = Field(default=None, pattern=r"^PORG-[A-F0-9]{16}$")
    organization_name: str | None = Field(default=None, min_length=2, max_length=120)
    expires_in_hours: int = Field(default=24, ge=1, le=168)

    @model_validator(mode="after")
    def validate_target(self) -> "InvitationCreate":
        self.email = self.email.casefold()
        if not EMAIL_PATTERN.fullmatch(self.email):
            raise ValueError("Adresse email invalide.")
        if not self.organization_id and not self.organization_name:
            raise ValueError("Indiquez une organisation existante ou un nom à créer.")
        return self


class InvitationView(BaseModel):
    id: str
    token: str | None = None
    organization_id: str
    role: DemoRole
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None
    delivery: Literal["local_demo_only"] = "local_demo_only"


class InvitationAcceptResult(BaseModel):
    membership_id: str
    organization_id: str
    role: DemoRole
    status: Literal["active"] = "active"


class RevocationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=3, max_length=500)


class SessionView(BaseModel):
    id: str
    user_id: str
    display_name: str
    active_membership_id: str
    created_at: datetime
    expires_at: datetime
    last_seen_at: datetime


class AdminActionView(BaseModel):
    id: str
    action: str
    subject_type: str
    subject_id: str
    decision: str | None = None
    reason: str
    actor_user_id: str
    actor_organization_id: str
    actor_role: str
    correlation_id: str
    payload: dict
    created_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sql_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class AdministrationService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def require_coordinator(actor: DemoActor) -> None:
        if actor.membership_status != "active" or actor.role != DemoRole.COORDINATOR:
            raise AdministrationPermissionError(
                "L’administration est réservée au coordinateur BioLoop actif."
            )

    def _record_action(
        self,
        session,
        *,
        action: str,
        subject_type: str,
        subject_id: str,
        actor: DemoActor,
        correlation_id: str,
        decision: str | None = None,
        reason: str = "",
        payload: dict | None = None,
    ) -> str:
        action_id = f"ADMIN-{uuid4().hex[:16].upper()}"
        session.execute(
            text(
                """
                INSERT INTO pilot_admin_actions
                    (id, action, subject_type, subject_id, decision, reason,
                     actor_user_id, actor_organization_id, actor_role,
                     correlation_id, payload_json, created_at)
                VALUES (:id, :action, :subject_type, :subject_id, :decision, :reason,
                        :actor_user_id, :actor_organization_id, :actor_role,
                        :correlation_id, :payload_json, :created_at)
                """
            ),
            {
                "id": action_id,
                "action": action,
                "subject_type": subject_type,
                "subject_id": subject_id,
                "decision": decision,
                "reason": reason,
                "actor_user_id": actor.user_id,
                "actor_organization_id": actor.organization_id,
                "actor_role": actor.role.value,
                "correlation_id": correlation_id,
                "payload_json": json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
                "created_at": _sql_datetime(_now()),
            },
        )
        return action_id

    def list_pending_memberships(self, actor: DemoActor) -> list[PendingMembership]:
        self.require_coordinator(actor)
        with self.database.session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT membership.id, membership.user_id, user.display_name,
                           membership.organization_id,
                           organization.name AS organization_name,
                           organization.kind AS organization_kind,
                           membership.role, membership.status, membership.created_at
                    FROM pilot_memberships membership
                    JOIN pilot_users user ON user.id = membership.user_id
                    JOIN pilot_organizations organization
                      ON organization.id = membership.organization_id
                    WHERE membership.status = 'pending'
                    ORDER BY membership.created_at, membership.id
                    """
                )
            ).mappings().all()
        return [PendingMembership.model_validate(dict(row)) for row in rows]

    def decide_membership(
        self,
        membership_id: str,
        data: MembershipDecisionCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> None:
        self.require_coordinator(actor)
        with self.database.session() as session:
            row = session.execute(
                text(
                    """
                    SELECT membership.id, membership.user_id, user.display_name,
                           membership.organization_id,
                           organization.name AS organization_name,
                           organization.kind AS organization_kind,
                           membership.role, membership.status, membership.created_at
                    FROM pilot_memberships membership
                    JOIN pilot_users user ON user.id = membership.user_id
                    JOIN pilot_organizations organization
                      ON organization.id = membership.organization_id
                    WHERE membership.id = :membership_id
                    """
                ),
                {"membership_id": membership_id},
            ).mappings().first()
            if row is None:
                raise AdministrationError("Appartenance pilote introuvable.")
            if row["user_id"] == actor.user_id:
                raise AdministrationPermissionError(
                    "Un utilisateur ne peut pas approuver ou refuser sa propre appartenance."
                )
            if row["status"] != "pending":
                raise AdministrationConflictError(
                    "Cette appartenance a déjà fait l’objet d’une décision."
                )
            if (
                data.decision == "approved"
                and row["organization_kind"] == "processing_unit"
                and data.processing_unit_id is None
            ):
                raise AdministrationError(
                    "L’approbation d’une unité exige son identifiant de site pilote."
                )
            new_status = "active" if data.decision == "approved" else "refused"
            session.execute(
                text(
                    """
                    UPDATE pilot_memberships
                    SET status = :status, approved_at = :decided_at,
                        approved_by_user_id = :actor_user_id
                    WHERE id = :membership_id AND status = 'pending'
                    """
                ),
                {
                    "status": new_status,
                    "decided_at": _sql_datetime(_now()),
                    "actor_user_id": actor.user_id,
                    "membership_id": membership_id,
                },
            )
            session.execute(
                text(
                    """
                    UPDATE pilot_organizations
                    SET approval_status = :status,
                        site_id = COALESCE(:site_id, site_id)
                    WHERE id = :organization_id
                    """
                ),
                {
                    "status": new_status,
                    "site_id": data.processing_unit_id,
                    "organization_id": row["organization_id"],
                },
            )
            if data.decision == "refused":
                session.execute(
                    text(
                        """
                        UPDATE pilot_sessions SET revoked_at = :decided_at
                        WHERE active_membership_id = :membership_id
                          AND revoked_at IS NULL
                        """
                    ),
                    {
                        "decided_at": _sql_datetime(_now()),
                        "membership_id": membership_id,
                    },
                )
            self._record_action(
                session,
                action="membership.decision",
                subject_type="pilot_membership",
                subject_id=membership_id,
                actor=actor,
                correlation_id=correlation_id,
                decision=data.decision,
                reason=data.reason,
                payload={
                    "organization_id": row["organization_id"],
                    "organization_kind": row["organization_kind"],
                    "processing_unit_id": data.processing_unit_id,
                    "new_status": new_status,
                },
            )

    def create_invitation(
        self,
        data: InvitationCreate,
        actor: DemoActor,
        *,
        correlation_id: str,
    ) -> InvitationView:
        self.require_coordinator(actor)
        token = secrets.token_urlsafe(32)
        invitation_id = f"PINV-{uuid4().hex[:16].upper()}"
        created_at = _now()
        expires_at = created_at + timedelta(hours=data.expires_in_hours)
        role = DemoRole(data.role)
        with self.database.session() as session:
            organization_id = data.organization_id
            if organization_id:
                organization = session.execute(
                    text("SELECT id FROM pilot_organizations WHERE id = :id"),
                    {"id": organization_id},
                ).first()
                if organization is None:
                    raise AdministrationError("Organisation pilote introuvable.")
            else:
                organization_id = f"PORG-{uuid4().hex[:16].upper()}"
                session.execute(
                    text(
                        """
                        INSERT INTO pilot_organizations
                            (id, name, kind, approval_status, is_demo, created_at, site_id)
                        VALUES (:id, :name, :kind, 'active', false, :created_at, NULL)
                        """
                    ),
                    {
                        "id": organization_id,
                        "name": data.organization_name,
                        "kind": data.role,
                        "created_at": _sql_datetime(created_at),
                    },
                )
            session.execute(
                text(
                    """
                    INSERT INTO pilot_role_invitations
                        (id, token_hash, email_digest, organization_id, role,
                         expires_at, used_at, created_at, invited_by_user_id,
                         used_by_user_id, revoked_at)
                    VALUES (:id, :token_hash, :email_digest, :organization_id, :role,
                            :expires_at, NULL, :created_at, :invited_by_user_id,
                            NULL, NULL)
                    """
                ),
                {
                    "id": invitation_id,
                    "token_hash": _digest(token),
                    "email_digest": _digest(data.email),
                    "organization_id": organization_id,
                    "role": role.value,
                    "expires_at": _sql_datetime(expires_at),
                    "created_at": _sql_datetime(created_at),
                    "invited_by_user_id": actor.user_id,
                },
            )
            self._record_action(
                session,
                action="invitation.created",
                subject_type="pilot_role_invitation",
                subject_id=invitation_id,
                actor=actor,
                correlation_id=correlation_id,
                payload={
                    "organization_id": organization_id,
                    "role": role.value,
                    "expires_at": expires_at.isoformat(),
                    "delivery": "local_demo_only",
                },
            )
        return InvitationView(
            id=invitation_id,
            token=token,
            organization_id=organization_id,
            role=role,
            expires_at=expires_at,
            created_at=created_at,
        )

    def accept_invitation(
        self,
        token: str,
        *,
        actor: DemoActor,
        email: str,
        correlation_id: str,
    ) -> InvitationAcceptResult:
        now = _now()
        with self.database.session() as session:
            row = session.execute(
                text(
                    """
                    SELECT * FROM pilot_role_invitations
                    WHERE token_hash = :token_hash
                    """
                ),
                {"token_hash": _digest(token)},
            ).mappings().first()
            if row is None:
                raise AdministrationError("Invitation invalide.")
            expires_at = row["expires_at"]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if row["used_at"] is not None or row["revoked_at"] is not None:
                raise AdministrationConflictError("Cette invitation n’est plus utilisable.")
            if expires_at <= now:
                raise AdministrationConflictError("Cette invitation a expiré.")
            if row["email_digest"] != _digest(email.casefold()):
                raise AdministrationPermissionError(
                    "Cette invitation ne correspond pas au compte connecté."
                )
            if row["invited_by_user_id"] == actor.user_id:
                raise AdministrationPermissionError(
                    "Un utilisateur ne peut pas valider sa propre invitation."
                )
            membership_id = f"PMEM-{uuid4().hex[:16].upper()}"
            try:
                session.execute(
                    text(
                        """
                        INSERT INTO pilot_memberships
                            (id, user_id, organization_id, role, status, created_at,
                             approved_at, approved_by_user_id)
                        VALUES (:id, :user_id, :organization_id, :role, 'active',
                                :created_at, :created_at, :approved_by_user_id)
                        """
                    ),
                    {
                        "id": membership_id,
                        "user_id": actor.user_id,
                        "organization_id": row["organization_id"],
                        "role": row["role"],
                        "created_at": _sql_datetime(now),
                        "approved_by_user_id": row["invited_by_user_id"],
                    },
                )
            except Exception as exc:
                raise AdministrationConflictError(
                    "Cette appartenance existe déjà."
                ) from exc
            session.execute(
                text(
                    """
                    UPDATE pilot_role_invitations
                    SET used_at = :used_at, used_by_user_id = :user_id
                    WHERE id = :id AND used_at IS NULL
                    """
                ),
                {"used_at": _sql_datetime(now), "user_id": actor.user_id, "id": row["id"]},
            )
            self._record_action(
                session,
                action="invitation.accepted",
                subject_type="pilot_role_invitation",
                subject_id=row["id"],
                actor=actor,
                correlation_id=correlation_id,
                decision="accepted",
                payload={
                    "membership_id": membership_id,
                    "organization_id": row["organization_id"],
                    "role": row["role"],
                },
            )
        return InvitationAcceptResult(
            membership_id=membership_id,
            organization_id=row["organization_id"],
            role=DemoRole(row["role"]),
        )

    def list_sessions(self, actor: DemoActor) -> list[SessionView]:
        self.require_coordinator(actor)
        with self.database.session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT pilot_sessions.id, pilot_sessions.user_id,
                           pilot_users.display_name,
                           pilot_sessions.active_membership_id,
                           pilot_sessions.created_at, pilot_sessions.expires_at,
                           pilot_sessions.last_seen_at
                    FROM pilot_sessions
                    JOIN pilot_users ON pilot_users.id = pilot_sessions.user_id
                    WHERE pilot_sessions.revoked_at IS NULL
                      AND pilot_sessions.expires_at > :now
                    ORDER BY pilot_sessions.created_at DESC
                    """
                ),
                {"now": _sql_datetime(_now())},
            ).mappings().all()
        return [SessionView.model_validate(dict(row)) for row in rows]

    def revoke_membership(
        self, membership_id: str, actor: DemoActor, *, reason: str, correlation_id: str
    ) -> None:
        self.require_coordinator(actor)
        if len(reason.strip()) < 3:
            raise AdministrationError("Un motif de révocation est requis.")
        with self.database.session() as session:
            row = session.execute(
                text("SELECT user_id, status FROM pilot_memberships WHERE id = :id"),
                {"id": membership_id},
            ).mappings().first()
            if row is None:
                raise AdministrationError("Appartenance pilote introuvable.")
            if row["user_id"] == actor.user_id:
                raise AdministrationPermissionError(
                    "Le coordinateur ne peut pas révoquer sa propre appartenance active."
                )
            if row["status"] == "revoked":
                raise AdministrationConflictError("Cette appartenance est déjà révoquée.")
            now = _now()
            session.execute(
                text("UPDATE pilot_memberships SET status = 'revoked' WHERE id = :id"),
                {"id": membership_id},
            )
            session.execute(
                text(
                    """
                    UPDATE pilot_sessions SET revoked_at = :now
                    WHERE active_membership_id = :id AND revoked_at IS NULL
                    """
                ),
                {"now": _sql_datetime(now), "id": membership_id},
            )
            self._record_action(
                session,
                action="membership.revoked",
                subject_type="pilot_membership",
                subject_id=membership_id,
                actor=actor,
                correlation_id=correlation_id,
                reason=reason,
            )

    def revoke_session(
        self, session_id: str, actor: DemoActor, *, reason: str, correlation_id: str
    ) -> None:
        self.require_coordinator(actor)
        if len(reason.strip()) < 3:
            raise AdministrationError("Un motif de révocation est requis.")
        with self.database.session() as session:
            cursor = session.execute(
                text(
                    """
                    UPDATE pilot_sessions SET revoked_at = :now
                    WHERE id = :id AND revoked_at IS NULL
                    """
                ),
                {"now": _sql_datetime(_now()), "id": session_id},
            )
            if cursor.rowcount != 1:
                raise AdministrationError("Session active introuvable.")
            self._record_action(
                session,
                action="session.revoked",
                subject_type="pilot_session",
                subject_id=session_id,
                actor=actor,
                correlation_id=correlation_id,
                reason=reason,
            )

    def list_history(self, actor: DemoActor, *, limit: int = 100) -> list[AdminActionView]:
        self.require_coordinator(actor)
        with self.database.session() as session:
            rows = session.execute(
                text(
                    """
                    SELECT * FROM pilot_admin_actions
                    ORDER BY created_at DESC, id DESC LIMIT :limit
                    """
                ),
                {"limit": limit},
            ).mappings().all()
        return [
            AdminActionView(
                id=row["id"],
                action=row["action"],
                subject_type=row["subject_type"],
                subject_id=row["subject_id"],
                decision=row["decision"],
                reason=row["reason"],
                actor_user_id=row["actor_user_id"],
                actor_organization_id=row["actor_organization_id"],
                actor_role=row["actor_role"],
                correlation_id=row["correlation_id"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]
