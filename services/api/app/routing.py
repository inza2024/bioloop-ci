from __future__ import annotations

import hashlib
from decimal import Decimal, ROUND_HALF_UP
from math import asin, cos, radians, sin, sqrt

from .models import ProcessingUnit, RoutePlan, RouteStop, WasteDeclaration


EARTH_MEAN_RADIUS_KM = 6371.0088


def straight_line_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Return a reproducible Haversine distance rounded to two decimals."""
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(
        radians, (lat1, lon1, lat2, lon2)
    )
    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    value = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    distance = 2 * EARTH_MEAN_RADIUS_KM * asin(sqrt(value))
    return float(Decimal(str(distance)).quantize(Decimal("0.01"), ROUND_HALF_UP))


def propose_route(
    declaration: WasteDeclaration, unit: ProcessingUnit, calculation_hash: str
) -> RoutePlan:
    one_way = Decimal(
        str(
            straight_line_distance_km(
                declaration.latitude,
                declaration.longitude,
                unit.latitude,
                unit.longitude,
            )
        )
    )
    total = (one_way * Decimal("2")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    route_hash = hashlib.sha256(
        (
            f"{declaration.id}:{unit.id}:{declaration.availability_date}:"
            f"{declaration.quantity_kg}:{one_way}:{calculation_hash}"
        ).encode("utf-8")
    ).hexdigest()
    return RoutePlan(
        id=f"ROUTE-{route_hash[:12].upper()}",
        status="proposée — validation humaine requise",
        method="Aller-retour direct par distance haversine ; aucun réseau routier ni trafic.",
        scheduled_date=declaration.availability_date,
        quantity_kg=declaration.quantity_kg,
        one_way_straight_line_km=one_way,
        total_straight_line_km=total,
        distance_unit="km géodésiques illustratifs",
        stops=[
            RouteStop(
                order=1,
                site_id=unit.id,
                name=unit.name,
                role="départ",
                window=unit.collection_window,
            ),
            RouteStop(
                order=2,
                site_id=declaration.producer_id,
                name=declaration.producer_name,
                role="collecte",
                window="À confirmer avec le producteur",
            ),
            RouteStop(
                order=3,
                site_id=unit.id,
                name=unit.name,
                role="livraison",
                window=unit.collection_window,
            ),
        ],
        assumptions=[
            "Les coordonnées des sites sont fictives et classées P0.",
            "La distance est géodésique et ne représente ni une route réelle, ni le trafic.",
            "La capacité et la fenêtre de collecte de l'unité sont simulées P0.",
            "Cette proposition ne déclenche aucune collecte ; un coordinateur doit la valider.",
        ],
    )
