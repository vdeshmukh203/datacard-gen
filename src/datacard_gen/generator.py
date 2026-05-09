"""DatacardGenerator — builds DataCard objects from CSV files or data structures."""

from __future__ import annotations

import csv
import io
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from .schema import DataCard, FieldInfo


# ── Statistics helpers ────────────────────────────────────────────────────── #

def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[str]) -> bool:
    non_empty = [v for v in values if str(v).strip()]
    if not non_empty:
        return False
    return sum(1 for v in non_empty if _safe_float(v) is not None) / len(non_empty) >= 0.8


def _field_stats(values: List[str]) -> Dict[str, Any]:
    non_empty = [v for v in values if str(v).strip()]
    total = len(values)
    missing = total - len(non_empty)
    stats: Dict[str, Any] = {
        "count": total,
        "missing": missing,
        "missing_pct": round(missing / total * 100, 2) if total else 0.0,
        "unique": len(set(non_empty)),
    }
    if _is_numeric(non_empty):
        nums = sorted(float(v) for v in non_empty if _safe_float(v) is not None)
        n = len(nums)
        if n:
            mean = sum(nums) / n
            mid = n // 2
            stats.update({
                "type": "numeric",
                "min": nums[0],
                "max": nums[-1],
                "mean": round(mean, 4),
                "std": round(math.sqrt(sum((x - mean) ** 2 for x in nums) / n), 4),
                "median": nums[mid] if n % 2 else (nums[mid - 1] + nums[mid]) / 2,
            })
    else:
        freq: Dict[str, int] = {}
        for v in non_empty:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        stats.update({
            "type": "categorical",
            "top_values": [{"value": k, "count": c} for k, c in top],
        })
    return stats


# ── Generator ─────────────────────────────────────────────────────────────── #

class DatacardGenerator:
    """Generates :class:`~datacard_gen.schema.DataCard` objects from various sources.

    Parameters
    ----------
    name:
        Human-readable dataset name.
    description:
        Free-text description of the dataset.
    license:
        SPDX license identifier (e.g. ``"cc-by-4.0"``).
    source:
        Source URL or citation string.
    tags:
        List of topic tags.
    version:
        Semantic version string for the dataset.
    """

    def __init__(
        self,
        name: str = "My Dataset",
        description: str = "A dataset.",
        license: str = "cc-by-4.0",
        source: str = "",
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
    ) -> None:
        self.name = name
        self.description = description
        self.license = license
        self.source = source
        self.tags = tags or []
        self.version = version

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _build_card(self, rows: List[Dict[str, str]]) -> DataCard:
        if not rows:
            return DataCard(
                name=self.name,
                description=self.description,
                num_rows=0,
                num_cols=0,
                license=self.license,
                source=self.source,
                tags=self.tags,
                version=self.version,
            )
        columns = list(rows[0].keys())
        fields: List[FieldInfo] = []
        for col in columns:
            values = [row.get(col, "") for row in rows]
            stats = _field_stats(values)
            dtype = stats.pop("type", "categorical")
            fields.append(FieldInfo(name=col, dtype=dtype, stats=stats))
        return DataCard(
            name=self.name,
            description=self.description,
            num_rows=len(rows),
            num_cols=len(columns),
            fields=fields,
            license=self.license,
            source=self.source,
            tags=self.tags,
            version=self.version,
        )

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def generate_from_csv(self, path: Path) -> DataCard:
        """Generate a :class:`DataCard` from a CSV file on disk.

        Raises :exc:`FileNotFoundError` if *path* does not exist.
        """
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"CSV file not found: {path}")
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_string(self, csv_text: str) -> DataCard:
        """Generate a :class:`DataCard` from a CSV-formatted string."""
        rows = [dict(r) for r in csv.DictReader(io.StringIO(csv_text))]
        return self._build_card(rows)

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        """Generate a :class:`DataCard` from a list of row dicts."""
        return self._build_card([{k: str(v) for k, v in row.items()} for row in data])

    def generate(self, source: Any) -> DataCard:
        """Generate a :class:`DataCard` from *source*.

        *source* may be:

        - a :class:`~pathlib.Path` or ``str`` → CSV file path
        - a ``list`` of dicts → :meth:`generate_from_dict`
        - a column-oriented ``dict`` (``{col: [values…]}``).
        """
        if isinstance(source, (str, Path)):
            return self.generate_from_csv(Path(source))
        if isinstance(source, list):
            return self.generate_from_dict(source)
        if isinstance(source, dict):
            keys = list(source.keys())
            if not keys:
                return self._build_card([])
            n = len(source[keys[0]])
            return self._build_card([{k: str(source[k][i]) for k in keys} for i in range(n)])
        raise TypeError(f"Unsupported source type: {type(source).__name__!r}")
