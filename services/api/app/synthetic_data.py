from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .models import ProcessingUnit, Producer, ProofLevel, Provenance, WasteType


SYNTHETIC_SEED = 20_260_830
SYNTHETIC_VERSION = "pilot-p0-fixed-seed-v1"


@dataclass(frozen=True)
class SyntheticDataset:
    metadata: dict
    producers: list[Producer]
    processing_units: list[ProcessingUnit]
    logistics: list[dict]
    availability: list[dict]
    operational_history: list[dict]
    clients: list[dict]
    transformations: list[dict]
    products: list[dict]
    quality_tests: list[dict]
    inventory_movements: list[dict]
    reservations: list[dict]

    def summary(self) -> dict:
        return {
            "metadata": self.metadata,
            "counts": {
                "producers": len(self.producers),
                "processing_units": len(self.processing_units),
                "logistics_organizations": len(self.logistics),
                "vehicles": sum(len(item["vehicles"]) for item in self.logistics),
                "availability_windows": len(self.availability),
                "historical_events": len(self.operational_history),
                "clients": len(self.clients),
                "transformations": len(self.transformations),
                "products": len(self.products),
                "quality_tests": len(self.quality_tests),
                "inventory_movements": len(self.inventory_movements),
                "reservations": len(self.reservations),
            },
        }


def build_enriched_dataset(
    base_producers: list[Producer],
    base_units: list[ProcessingUnit],
    waste_types: list[WasteType],
) -> SyntheticDataset:
    rng = random.Random(SYNTHETIC_SEED)
    localities = [
        "Abobo",
        "Adjamé",
        "Anyama",
        "Bingerville",
        "Cocody",
        "Koumassi",
        "Marcory",
        "Port-Bouët",
        "Songon",
        "Yopougon",
    ]
    kinds = ["Marché", "Élevage", "Cantine", "Coopérative", "Agro-transformateur"]
    waste_ids = [item.id for item in waste_types]
    producers = list(base_producers)
    for index in range(len(producers) + 1, 41):
        locality = localities[(index - 1) % len(localities)]
        waste_id = waste_ids[(index - 1) % len(waste_ids)]
        producers.append(
            Producer(
                id=f"PROD-{index:03d}",
                name=f"Site pilote fictif {index:02d} — {locality}",
                kind=kinds[(index - 1) % len(kinds)],
                locality=locality,
                latitude=round(5.25 + rng.random() * 0.35, 6),
                longitude=round(-4.25 + rng.random() * 0.35, 6),
                default_waste_type_id=waste_id,
                provenance=Provenance.SIMULATED,
                proof_level=ProofLevel.P0,
            )
        )

    units = list(base_units)
    unit_specs = [
        ("UNIT-003", "Unité fictive Anyama Nord", "Méthanisation pilote illustrative", "Anyama"),
        ("UNIT-004", "Plateforme fictive Port-Bouët", "Compostage contrôlé illustratif", "Port-Bouët"),
    ]
    for offset, (identifier, name, process, locality) in enumerate(unit_specs):
        units.append(
            ProcessingUnit(
                id=identifier,
                name=name,
                process=process,
                locality=locality,
                latitude=round(5.37 + rng.random() * 0.12, 6),
                longitude=round(-4.15 + rng.random() * 0.14, 6),
                daily_capacity_kg=Decimal(str(7_000 + offset * 2_000)),
                reserved_capacity_kg=Decimal(str(1_250 + offset * 500)),
                accepted_waste_type_ids=waste_ids[: 2 + offset],
                collection_window="07:00–15:00 — fenêtre fictive P0",
                provenance=Provenance.SIMULATED,
                proof_level=ProofLevel.P0,
            )
        )

    logistics = []
    for org_index in range(1, 4):
        logistics.append(
            {
                "id": f"P0-LOG-{org_index:02d}",
                "name": f"Collecteur fictif {org_index}",
                "provenance": "simulated",
                "proof_level": "P0",
                "vehicles": [
                    {
                        "id": f"P0-VEH-{org_index:02d}-{vehicle_index}",
                        "capacity_kg": 1_500 + 500 * vehicle_index + 250 * org_index,
                        "capacity_unit": "kg de matière fraîche — fictif",
                        "proof_level": "P0",
                    }
                    for vehicle_index in (1, 2)
                ],
            }
        )

    frequencies = ["quotidienne", "hebdomadaire", "ponctuelle"]
    availability = [
        {
            "producer_id": producer.id,
            "frequency": frequencies[index % len(frequencies)],
            "available_from": (date(2026, 9, 1) + timedelta(days=index % 14)).isoformat(),
            "collection_window": f"{6 + index % 4:02d}:00–{10 + index % 5:02d}:00",
            "quantity_kg": 250 + (index * 137) % 3_500,
            "quantity_unit": "kg de matière fraîche déclarée fictive",
            "proof_level": "P0",
        }
        for index, producer in enumerate(producers)
    ]

    decisions = ["accepted", "refused", "pending"]
    history = []
    for index in range(72):
        producer = producers[index % len(producers)]
        declared = 300 + (index * 173) % 4_000
        delta = ((index % 9) - 4) * 12
        history.append(
            {
                "id": f"P0-HIST-{index + 1:03d}",
                "producer_id": producer.id,
                "waste_type_id": producer.default_waste_type_id,
                "declared_quantity_kg": declared,
                "declared_event_type": "simulated declaration history",
                "declared_proof_level": "P0",
                "measured_quantity_kg": max(1, declared + delta),
                "measurement_event_type": "simulated measurement history",
                "measured_proof_level": "P0",
                "decision": decisions[index % len(decisions)],
                "decision_event_type": "simulated decision history",
                "decision_proof_level": "P0",
                "occurred_on": (date(2026, 6, 1) + timedelta(days=index)).isoformat(),
                "provenance": "simulated",
            }
        )

    clients = [
        {
            "id": f"P0-CLIENT-{index:02d}",
            "name": f"Client agricole fictif {index}",
            "locality": localities[(index * 3) % len(localities)],
            "interest": "produit qualifié à confirmer — aucune disponibilité inventée",
            "proof_level": "P0",
        }
        for index in range(1, 9)
    ]
    transformations = [
        {
            "id": f"P0-TRUN-{index:02d}",
            "processing_unit_id": units[index % len(units)].id,
            "process": units[index % len(units)].process,
            "input_quantity_kg": 800 + index * 175,
            "input_unit": "kg",
            "duration_hours": 18 + index * 6,
            "loss_quantity_kg": 25 + index * 5,
            "status": "completed" if index < 4 else "in_progress",
            "provenance": "simulated",
            "proof_level": "P0",
            "scientific_validation": False,
        }
        for index in range(6)
    ]
    product_categories = [
        "measured_biogas",
        "raw_digestate",
        "liquid_fraction",
        "solid_fraction",
        "compost_amendment",
        "potential_fertilizing_product",
    ]
    products = [
        {
            "id": f"P0-PRODUCT-{index + 1:02d}",
            "transformation_id": transformations[index % len(transformations)]["id"],
            "category": category,
            "quantity": 110 + index * 37,
            "unit": "m3" if category == "measured_biogas" else "kg",
            "quality_status": "released" if index in {0, 4} else "quarantine",
            "measurement_method": "méthode fictive non validée",
            "provenance": "simulated",
            "proof_level": "P0",
            "commercial_claim_authorized": False,
        }
        for index, category in enumerate(product_categories)
    ]
    quality_tests = [
        {
            "id": f"P0-QTEST-{index + 1:02d}",
            "product_id": product["id"],
            "parameter": "paramètre qualité fictif",
            "value": str(10 + index),
            "unit": "unité fictive",
            "method": "protocole fictif non accrédité",
            "provenance": "simulated",
            "proof_level": "P0",
        }
        for index, product in enumerate(products)
    ]
    inventory_movements = [
        {
            "id": f"P0-MOVE-{index + 1:02d}",
            "product_id": product["id"],
            "movement_type": "production",
            "quantity": product["quantity"],
            "unit": product["unit"],
            "provenance": "simulated",
            "proof_level": "P0",
        }
        for index, product in enumerate(products)
    ]
    reservations = [
        {
            "id": f"P0-RES-{index + 1:02d}",
            "product_id": product["id"],
            "client_id": clients[index]["id"],
            "quantity": 20 + index * 5,
            "unit": product["unit"],
            "status": "active",
            "provenance": "simulated",
            "proof_level": "P0",
        }
        for index, product in enumerate(
            product for product in products if product["quality_status"] == "released"
        )
    ]
    metadata = {
        "profile": "enriched",
        "version": SYNTHETIC_VERSION,
        "seed": SYNTHETIC_SEED,
        "provenance": "simulated",
        "proof_level": "P0",
        "classification": "jeu synthétique déterministe — démonstration uniquement",
        "preserves_fixture_ids": True,
        "scientific_validation": False,
    }
    return SyntheticDataset(
        metadata=metadata,
        producers=producers,
        processing_units=units,
        logistics=logistics,
        availability=availability,
        operational_history=history,
        clients=clients,
        transformations=transformations,
        products=products,
        quality_tests=quality_tests,
        inventory_movements=inventory_movements,
        reservations=reservations,
    )
