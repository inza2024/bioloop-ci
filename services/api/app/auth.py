from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from .database import Database
from .models import DemoActor, DemoRole


SESSION_COOKIE = "bioloop_session"
CSRF_COOKIE = "bioloop_csrf"
CSRF_HEADER = "X-CSRF-Token"
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SELF_SERVICE: dict[str, tuple[DemoRole, Literal["active", "pending"]]] = {
    "producer": (DemoRole.PRODUCER, "active"),
    "client": (DemoRole.CLIENT, "active"),
    "logistician": (DemoRole.LOGISTICIAN, "pending"),
    "processing_unit": (DemoRole.UNIT_OPERATOR, "pending"),
}
SENSITIVE_ORGANIZATION_TYPES = {"field_controller", "bioloop_coordinator"}


class AuthError(ValueError):
    pass


class AuthConflictError(AuthError):
    pass


class AuthPermissionError(AuthError):
    pass


class AuthRateLimitError(AuthError):
    pass


class RegistrationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    display_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    organization_name: str = Field(min_length=2, max_length=120)
    organization_type: Literal[
        "producer",
        "client",
        "logistician",
        "processing_unit",
        "field_controller",
        "bioloop_coordinator",
    ]

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.casefold()
        if not EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Adresse email invalide.")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not (any(item.islower() for item in value) and any(item.isupper() for item in value)):
            raise ValueError("Le mot de passe doit contenir une minuscule et une majuscule.")
        if not any(item.isdigit() for item in value):
            raise ValueError("Le mot de passe doit contenir un chiffre.")
        return value


class LoginCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class MembershipView(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    organization_kind: str
    site_id: str | None = None
    role: DemoRole
    status: Literal["active", "pending"]


class AuthUserView(BaseModel):
    id: str
    display_name: str
    email: str


class AuthContext(BaseModel):
    user: AuthUserView
    active_membership: MembershipView
    memberships: list[MembershipView]
    actor: DemoActor
    portal_path: str
    pilot_security_label: str = (
        "authentification pilote locale — non certifiée pour la production"
    )


@dataclass(frozen=True)
class SessionGrant:
    token: str
    context: AuthContext


def _now() -> datetime:
    return datetime.now(UTC)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _datetime(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _sql_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_matches(cookie_value: str | None, header_value: str | None) -> bool:
    if not cookie_value or not header_value:
        return False
    return hmac.compare_digest(cookie_value, header_value)


class AuthService:
    def __init__(self, database: Database, *, session_ttl_seconds: int) -> None:
        self.database = database
        self.session_ttl = timedelta(seconds=session_ttl_seconds)
        self.password_hasher = PasswordHasher()
        self._dummy_hash = self.password_hasher.hash("BioLoop-Dummy-Password-2026")

    @staticmethod
    def _portal_path(role: DemoRole) -> str:
        return f"/portal/{role.value}"

    def register(self, data: RegistrationCreate) -> SessionGrant:
        if data.organization_type in SENSITIVE_ORGANIZATION_TYPES:
            raise AuthPermissionError(
                "Ce rôle sensible exige une invitation et une approbation administrateur."
            )
        role, membership_status = SELF_SERVICE[data.organization_type]
        user_id = f"PUSER-{uuid4().hex[:16].upper()}"
        organization_id = f"PORG-{uuid4().hex[:16].upper()}"
        membership_id = f"PMEM-{uuid4().hex[:16].upper()}"
        created_at = _now()
        try:
            with self.database.session() as session:
                exists = session.execute(
                    text("SELECT 1 FROM pilot_users WHERE email_normalized = :email"),
                    {"email": data.email.casefold()},
                ).first()
                if exists:
                    raise AuthConflictError("Impossible de créer ce compte.")
                session.execute(
                    text(
                        """
                        INSERT INTO pilot_users
                            (id, display_name, email_normalized, password_hash, status, created_at)
                        VALUES (:id, :name, :email, :password_hash, 'active', :created_at)
                        """
                    ),
                    {
                        "id": user_id,
                        "name": data.display_name,
                        "email": data.email.casefold(),
                        "password_hash": self.password_hasher.hash(data.password),
                        "created_at": _sql_datetime(created_at),
                    },
                )
                session.execute(
                    text(
                        """
                        INSERT INTO pilot_organizations
                            (id, name, kind, approval_status, is_demo, created_at)
                        VALUES (:id, :name, :kind, :status, false, :created_at)
                        """
                    ),
                    {
                        "id": organization_id,
                        "name": data.organization_name,
                        "kind": data.organization_type,
                        "status": membership_status,
                        "created_at": _sql_datetime(created_at),
                    },
                )
                session.execute(
                    text(
                        """
                        INSERT INTO pilot_memberships
                            (id, user_id, organization_id, role, status, created_at, approved_at)
                        VALUES (:id, :user_id, :organization_id, :role, :status,
                                :created_at, :approved_at)
                        """
                    ),
                    {
                        "id": membership_id,
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "role": role.value,
                        "status": membership_status,
                        "created_at": _sql_datetime(created_at),
                        "approved_at": _sql_datetime(created_at) if membership_status == "active" else None,
                    },
                )
        except AuthError:
            raise
        return self._create_session(user_id, membership_id)

    def _login_is_limited(self, email_digest: str, ip_digest: str) -> bool:
        window_start = _now() - timedelta(minutes=15)
        with self.database.session() as session:
            failures = session.execute(
                text(
                    """
                    SELECT COUNT(*) FROM pilot_login_attempts
                    WHERE email_digest = :email_digest AND ip_digest = :ip_digest
                      AND success = false AND attempted_at >= :window_start
                    """
                ),
                {
                    "email_digest": email_digest,
                    "ip_digest": ip_digest,
                    "window_start": _sql_datetime(window_start),
                },
            ).scalar_one()
        return int(failures) >= 5

    def _record_login_attempt(
        self, email_digest: str, ip_digest: str, *, success: bool
    ) -> None:
        with self.database.session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO pilot_login_attempts
                        (id, email_digest, ip_digest, success, attempted_at)
                    VALUES (:id, :email_digest, :ip_digest, :success, :attempted_at)
                    """
                ),
                {
                    "id": f"PATT-{uuid4().hex[:16].upper()}",
                    "email_digest": email_digest,
                    "ip_digest": ip_digest,
                    "success": success,
                    "attempted_at": _sql_datetime(_now()),
                },
            )

    def login(self, data: LoginCreate, *, client_ip: str) -> SessionGrant:
        email = data.email.casefold()
        email_digest = _digest(email)
        ip_digest = _digest(client_ip or "unknown")
        if self._login_is_limited(email_digest, ip_digest):
            raise AuthRateLimitError("Trop de tentatives. Réessayez plus tard.")
        with self.database.session() as session:
            user = session.execute(
                text(
                    """
                    SELECT id, password_hash FROM pilot_users
                    WHERE email_normalized = :email AND status = 'active'
                    """
                ),
                {"email": email},
            ).mappings().first()
        valid = False
        try:
            valid = self.password_hasher.verify(
                user["password_hash"] if user else self._dummy_hash,
                data.password,
            )
        except (VerifyMismatchError, InvalidHashError):
            valid = False
        if not user or not valid:
            self._record_login_attempt(email_digest, ip_digest, success=False)
            raise AuthError("Email ou mot de passe incorrect.")
        with self.database.session() as session:
            membership = session.execute(
                text(
                    """
                    SELECT id FROM pilot_memberships
                    WHERE user_id = :user_id AND status IN ('active', 'pending')
                    ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, created_at
                    LIMIT 1
                    """
                ),
                {"user_id": user["id"]},
            ).first()
        if membership is None:
            self._record_login_attempt(email_digest, ip_digest, success=False)
            raise AuthError("Email ou mot de passe incorrect.")
        self._record_login_attempt(email_digest, ip_digest, success=True)
        return self._create_session(user["id"], membership[0])

    def _create_session(self, user_id: str, membership_id: str) -> SessionGrant:
        token = secrets.token_urlsafe(32)
        created_at = _now()
        with self.database.session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO pilot_sessions
                        (id, token_hash, user_id, active_membership_id, created_at,
                         expires_at, last_seen_at, revoked_at)
                    VALUES (:id, :token_hash, :user_id, :membership_id, :created_at,
                            :expires_at, :created_at, NULL)
                    """
                ),
                {
                    "id": f"PSESS-{uuid4().hex[:16].upper()}",
                    "token_hash": _digest(token),
                    "user_id": user_id,
                    "membership_id": membership_id,
                    "created_at": _sql_datetime(created_at),
                    "expires_at": _sql_datetime(created_at + self.session_ttl),
                },
            )
        context = self.resolve(token)
        assert context is not None
        return SessionGrant(token=token, context=context)

    def resolve(self, token: str | None) -> AuthContext | None:
        if not token:
            return None
        now = _now()
        with self.database.session() as session:
            session_row = session.execute(
                text(
                    """
                    SELECT id, user_id, active_membership_id, expires_at, revoked_at
                    FROM pilot_sessions WHERE token_hash = :token_hash
                    """
                ),
                {"token_hash": _digest(token)},
            ).mappings().first()
            if (
                session_row is None
                or session_row["revoked_at"] is not None
                or _datetime(session_row["expires_at"]) <= now
            ):
                return None
            session.execute(
                text("UPDATE pilot_sessions SET last_seen_at = :now WHERE id = :id"),
                {"now": _sql_datetime(now), "id": session_row["id"]},
            )
            user = session.execute(
                text(
                    "SELECT id, display_name, email_normalized FROM pilot_users WHERE id = :id AND status = 'active'"
                ),
                {"id": session_row["user_id"]},
            ).mappings().first()
            memberships = session.execute(
                text(
                    """
                    SELECT membership.id, membership.organization_id,
                           organization.name AS organization_name,
                           organization.kind AS organization_kind,
                           organization.site_id,
                           membership.role, membership.status
                    FROM pilot_memberships membership
                    JOIN pilot_organizations organization
                      ON organization.id = membership.organization_id
                    WHERE membership.user_id = :user_id
                      AND membership.status IN ('active', 'pending')
                    ORDER BY membership.created_at, membership.id
                    """
                ),
                {"user_id": session_row["user_id"]},
            ).mappings().all()
        if user is None:
            return None
        membership_views = [MembershipView.model_validate(dict(row)) for row in memberships]
        active = next(
            (item for item in membership_views if item.id == session_row["active_membership_id"]),
            None,
        )
        if active is None:
            return None
        actor = DemoActor(
            user_id=user["id"],
            display_name=user["display_name"],
            organization_id=active.organization_id,
            organization_name=active.organization_name,
            role=active.role,
            site_type=(
                "processing_unit"
                if active.organization_kind == "processing_unit"
                else "producer" if active.organization_kind == "producer" else None
            ),
            site_id=active.site_id,
            is_demo=False,
            authenticated_for_pilot=True,
            authenticated_for_production=False,
            membership_id=active.id,
            membership_status=active.status,
        )
        return AuthContext(
            user=AuthUserView(
                id=user["id"],
                display_name=user["display_name"],
                email=user["email_normalized"],
            ),
            active_membership=active,
            memberships=membership_views,
            actor=actor,
            portal_path=self._portal_path(active.role),
        )

    def switch_membership(
        self, token: str, membership_id: str
    ) -> AuthContext:
        context = self.resolve(token)
        if context is None:
            raise AuthError("Session invalide ou expirée.")
        if not any(item.id == membership_id for item in context.memberships):
            raise AuthPermissionError("Cette appartenance n’est pas accessible.")
        with self.database.session() as session:
            session.execute(
                text(
                    """
                    UPDATE pilot_sessions SET active_membership_id = :membership_id
                    WHERE token_hash = :token_hash AND revoked_at IS NULL
                    """
                ),
                {"membership_id": membership_id, "token_hash": _digest(token)},
            )
        updated = self.resolve(token)
        assert updated is not None
        return updated

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self.database.session() as session:
            session.execute(
                text(
                    """
                    UPDATE pilot_sessions SET revoked_at = :revoked_at
                    WHERE token_hash = :token_hash AND revoked_at IS NULL
                    """
                ),
                {"revoked_at": _sql_datetime(_now()), "token_hash": _digest(token)},
            )
