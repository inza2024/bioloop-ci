from __future__ import annotations

import json
from pathlib import Path

from .models import ProcessingUnit, Producer, WasteType


class Catalog:
    def __init__(self, fixtures_dir: Path) -> None:
        self.producers = self._load(fixtures_dir / "producers.json", Producer)
        self.processing_units = self._load(
            fixtures_dir / "processing_units.json", ProcessingUnit
        )
        self.waste_types = self._load(
            fixtures_dir / "waste_types.json", WasteType
        )
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

