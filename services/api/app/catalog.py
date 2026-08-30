from __future__ import annotations

import json
from pathlib import Path

from .models import ProcessingUnit, Producer, WasteType
from .synthetic_data import SyntheticDataset, build_enriched_dataset


class Catalog:
    def __init__(self, fixtures_dir: Path, profile: str = "small") -> None:
        self.producers = self._load(fixtures_dir / "producers.json", Producer)
        self.processing_units = self._load(
            fixtures_dir / "processing_units.json", ProcessingUnit
        )
        self.waste_types = self._load(
            fixtures_dir / "waste_types.json", WasteType
        )
        enriched = build_enriched_dataset(
            self.producers, self.processing_units, self.waste_types
        )
        if profile == "enriched":
            self.synthetic_dataset = enriched
            self.producers = enriched.producers
            self.processing_units = enriched.processing_units
        elif profile == "small":
            self.synthetic_dataset = SyntheticDataset(
                metadata={
                    "profile": "small",
                    "version": "legacy-small-fixtures-v1",
                    "seed": None,
                    "provenance": "simulated",
                    "proof_level": "P0",
                    "classification": "petit jeu fictif historique",
                    "scientific_validation": False,
                },
                producers=list(self.producers),
                processing_units=list(self.processing_units),
                logistics=[],
                availability=[],
                operational_history=[],
                clients=[],
            )
        elif profile != "small":
            raise ValueError("BIOLOOP_SYNTHETIC_PROFILE doit valoir 'small' ou 'enriched'.")
        self.profile = profile
        self._producers = {item.id: item for item in self.producers}
        self._units = {item.id: item for item in self.processing_units}
        self._waste_types = {item.id: item for item in self.waste_types}

    @staticmethod
    def _load(path: Path, model: type[Producer] | type[ProcessingUnit] | type[WasteType]):
        with path.open(encoding="utf-8") as stream:
            rows = json.load(stream)
        return [model.model_validate(row) for row in rows]

    def producer(self, producer_id: str) -> Producer | None:
        return self._producers.get(producer_id)

    def processing_unit(self, unit_id: str) -> ProcessingUnit | None:
        return self._units.get(unit_id)

    def waste_type(self, waste_type_id: str) -> WasteType | None:
        return self._waste_types.get(waste_type_id)
