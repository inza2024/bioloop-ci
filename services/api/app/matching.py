from __future__ import annotations

from decimal import Decimal

from .catalog import Catalog
from .models import UnitMatch, WasteDeclaration
from .routing import straight_line_distance_km


def compatible_units(
    declaration: WasteDeclaration, catalog: Catalog
) -> list[UnitMatch]:
    matches: list[UnitMatch] = []
    for unit in catalog.processing_units:
        available = unit.daily_capacity_kg - unit.reserved_capacity_kg
        if declaration.waste_type_id not in unit.accepted_waste_type_ids:
            continue
        if declaration.quantity_kg > available:
            continue
        distance = straight_line_distance_km(
            declaration.latitude,
            declaration.longitude,
            unit.latitude,
            unit.longitude,
        )
        matches.append(
            UnitMatch(
                processing_unit_id=unit.id,
                processing_unit_name=unit.name,
                process=unit.process,
                available_capacity_kg=available,
                distance_straight_line_km=Decimal(str(distance)),
                collection_window=unit.collection_window,
                reasons=[
                    "Type de déchet présent dans la liste d'acceptation P0 de l'unité.",
                    "Quantité inférieure ou égale à la capacité disponible P0.",
                    "Classement par distance géodésique illustrative croissante.",
                ],
            )
        )
    return sorted(matches, key=lambda item: (item.distance_straight_line_km, item.processing_unit_id))

