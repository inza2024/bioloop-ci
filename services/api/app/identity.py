from __future__ import annotations

import json
import re
from pathlib import Path

from .models import (
    DemoActor,
    DemoMembership,
    DemoOrganization,
    DemoRole,
    DemoUser,
)


DEMO_USER_ID_PATTERN = re.compile(r"^USER-[A-Z0-9-]{3,40}$")
DEFAULT_DEMO_USER_ID = "USER-COORD-001"


PERMISSIONS: dict[DemoRole, list[str]] = {
    DemoRole.PRODUCER: [
        "declaration:create:own",
        "declaration:read:own",
        "evidence:create:own",
    ],
    DemoRole.LOGISTICIAN: [
        "collection:read:assigned",
        "collection:confirm:assigned",
        "evidence:create:assigned",
        "measurement:create:assigned",
        "lot:create:assigned",
    ],
    DemoRole.UNIT_OPERATOR: [
        "lot:read:own_unit",
        "lot:decide:own_unit",
        "projection:read:own_unit",
    ],
    DemoRole.FIELD_CONTROLLER: [
        "control:read:pending",
        "verification:create:p4",
    ],
    DemoRole.COORDINATOR: [
        "overview:read:any",
        "audit:read:any",
        "demo:operate:any",
    ],
    DemoRole.CLIENT: ["product:read:represented"],
}


class IdentityError(ValueError):
    pass


class IdentityDirectory:
    def __init__(self, fixture_path: Path) -> None:
        with fixture_path.open(encoding="utf-8") as stream:
            payload = json.load(stream)
        self.organizations = [
            DemoOrganization.model_validate(item)
            for item in payload["organizations"]
        ]
        self.users = [DemoUser.model_validate(item) for item in payload["users"]]
        self.memberships = [
            DemoMembership.model_validate(item)
            for item in payload["memberships"]
        ]
        self._organizations = {item.id: item for item in self.organizations}
        self._users = {item.id: item for item in self.users}
        self._memberships = {item.user_id: item for item in self.memberships}
        self._actors = {user.id: self._build_actor(user.id) for user in self.users}

    def _build_actor(self, user_id: str) -> DemoActor:
        user = self._users[user_id]
        membership = self._memberships[user_id]
        organization = self._organizations[membership.organization_id]
        return DemoActor(
            user_id=user.id,
            display_name=user.display_name,
            organization_id=organization.id,
            organization_name=organization.name,
            role=membership.role,
            site_type=organization.site_type,
            site_id=organization.site_id,
        )

    @property
    def actors(self) -> list[DemoActor]:
        return [self._actors[user.id] for user in self.users]

    def actor(self, user_id: str) -> DemoActor:
        if not DEMO_USER_ID_PATTERN.fullmatch(user_id):
            raise IdentityError("Identifiant d’utilisateur de démonstration invalide.")
        actor = self._actors.get(user_id)
        if actor is None:
            raise IdentityError("Utilisateur de démonstration inconnu ou inactif.")
        return actor

    def organization(self, organization_id: str) -> DemoOrganization | None:
        return self._organizations.get(organization_id)

    def organization_for_site(
        self, site_type: str, site_id: str
    ) -> DemoOrganization | None:
        return next(
            (
                organization
                for organization in self.organizations
                if organization.site_type == site_type
                and organization.site_id == site_id
            ),
            None,
        )

    def organization_for_role(self, role: DemoRole) -> DemoOrganization | None:
        membership = next(
            (item for item in self.memberships if item.role == role), None
        )
        return (
            self._organizations.get(membership.organization_id)
            if membership
            else None
        )

    def permissions(self, actor: DemoActor) -> list[str]:
        return list(PERMISSIONS[actor.role])

    def can_operate_any(self, actor: DemoActor) -> bool:
        return actor.role == DemoRole.COORDINATOR
