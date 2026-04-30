from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._core import _field_stats
from .models import DataCard, FieldInfo


class DatacardGenerator:
    """Profiles a dataset and produces a :class:`DataCard`."""

    def __init__(
        self,
        name: str = "My Dataset",
        description: str = "A dataset.",
        license: str = "cc-by-4.0",
        source: str = "",
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
    ):
        self.name = name
        self.description = description
        self.license = license
        self.source = source
        self.tags = tags or []
        self.version = version

    def _build_card(self, rows: List[Dict[str, str]]) -> DataCard:
        if not rows:
            return DataCard(
                name=self.name, description=self.description,
                num_rows=0, num_cols=0,
                license=self.license, source=self.source,
                tags=self.tags, version=self.version,
            )
        columns = list(rows[0].keys())
        fields: List[FieldInfo] = []
        for col in columns:
            values = [row.get(col, "") for row in rows]
            stats = _field_stats(values)
            dtype = stats.pop("type", "categorical")
            fields.append(FieldInfo(name=col, dtype=dtype, stats=stats))
        return DataCard(
            name=self.name, description=self.description,
            num_rows=len(rows), num_cols=len(columns), fields=fields,
            license=self.license, source=self.source,
            tags=self.tags, version=self.version,
        )

    def generate_from_csv(self, path: Path) -> DataCard:
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_json(self, path: Path) -> DataCard:
        """Accept a JSON file containing either a list of records or a column-oriented dict."""
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            rows: List[Dict[str, str]] = [{k: str(v) for k, v in rec.items()} for rec in data]
        elif isinstance(data, dict):
            keys = list(data.keys())
            if not keys:
                return self._build_card([])
            n = len(data[keys[0]])
            rows = [{k: str(data[k][i]) for k in keys} for i in range(n)]
        else:
            raise ValueError("JSON must be a list of records or a column-oriented dict.")
        return self._build_card(rows)

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        return self._build_card([{k: str(v) for k, v in row.items()} for row in data])

    def generate(self, source: Any) -> DataCard:
        """Dispatch to the appropriate loader based on *source* type or file extension."""
        if isinstance(source, Path):
            if source.suffix.lower() == ".json":
                return self.generate_from_json(source)
            return self.generate_from_csv(source)
        if isinstance(source, list):
            return self.generate_from_dict(source)
        if isinstance(source, dict):
            keys = list(source.keys())
            if not keys:
                return self._build_card([])
            n = len(source[keys[0]])
            return self._build_card([{k: str(source[k][i]) for k in keys} for i in range(n)])
        raise TypeError(f"Unsupported source type: {type(source)}")
