"""Core datacard generation logic for the datacard_gen package."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    """Return *v* as float, or None if conversion fails."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[str]) -> bool:
    """Return True when ≥ 80 % of non-empty *values* parse as floats."""
    non_empty = [v for v in values if str(v).strip()]
    if not non_empty:
        return False
    parseable = sum(1 for v in non_empty if _safe_float(v) is not None)
    return parseable / len(non_empty) >= 0.8


def _percentile(sorted_nums: List[float], pct: float) -> float:
    n = len(sorted_nums)
    if n == 0:
        return 0.0
    idx = pct / 100.0 * (n - 1)
    lo, hi = int(idx), min(int(idx) + 1, n - 1)
    return round(sorted_nums[lo] + (sorted_nums[hi] - sorted_nums[lo]) * (idx - lo), 4)


def _field_stats(values: List[str]) -> Dict[str, Any]:
    """Compute per-column statistics for a list of string values."""
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
            stats.update({
                "type": "numeric",
                "min": nums[0],
                "max": nums[-1],
                "mean": round(mean, 4),
                "std": round(math.sqrt(sum((x - mean) ** 2 for x in nums) / n), 4),
                "median": _percentile(nums, 50),
                "q1": _percentile(nums, 25),
                "q3": _percentile(nums, 75),
            })
    else:
        freq: Dict[str, int] = {}
        for v in non_empty:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        stats.update({
            "type": "categorical",
            "top_values": [{"value": k, "count": v} for k, v in top],
        })
    return stats


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class FieldInfo:
    """Name, detected type, and summary statistics for one dataset column."""

    def __init__(self, name: str, dtype: str, stats: Dict[str, Any]) -> None:
        self.name = name
        self.dtype = dtype
        self.stats = stats

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


class DataCard:
    """A structured, serialisable dataset documentation card."""

    def __init__(
        self,
        name: str,
        description: str,
        num_rows: int,
        num_cols: int,
        fields: Optional[List[FieldInfo]] = None,
        tags: Optional[List[str]] = None,
        license: str = "unknown",
        source: str = "",
        version: str = "1.0.0",
        examples: Optional[List[Dict[str, str]]] = None,
    ) -> None:
        self.name = name
        self.description = description
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.fields: List[FieldInfo] = fields or []
        self.tags: List[str] = tags or []
        self.license = license
        self.source = source
        self.version = version
        self.examples: List[Dict[str, str]] = examples or []

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "license": self.license,
            "source": self.source,
            "version": self.version,
            "tags": self.tags,
            "fields": [f.to_dict() for f in self.fields],
        }
        if self.examples:
            d["examples"] = self.examples
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialise to JSON string."""
        import json as _json
        return _json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render a Hugging Face-compatible Markdown datacard."""
        lines = [
            "---",
            f"pretty_name: {self.name}",
            f"license: {self.license}",
            f"version: {self.version}",
        ]
        if self.tags:
            lines.append("tags:")
            for t in self.tags:
                lines.append(f"  - {t}")
        lines += [
            "---", "",
            f"# {self.name}", "",
            "## Dataset Description", "",
            self.description, "",
            "## Dataset Structure", "",
            f"- **Rows:** {self.num_rows:,}",
            f"- **Columns:** {self.num_cols}",
        ]
        if self.source:
            lines.append(f"- **Source:** {self.source}")
        lines += ["", "## Data Fields", ""]
        for fi in self.fields:
            s = fi.stats
            lines += [
                f"### `{fi.name}` ({fi.dtype})", "",
                f"- **Missing:** {s.get('missing', 0)} ({s.get('missing_pct', 0):.1f}%)",
                f"- **Unique values:** {s.get('unique', '?')}",
            ]
            if fi.dtype == "numeric":
                lines += [
                    f"- **Min:** {s.get('min')}",
                    f"- **Max:** {s.get('max')}",
                    f"- **Mean:** {s.get('mean')}",
                    f"- **Std:** {s.get('std')}",
                    f"- **Median:** {s.get('median')}",
                    f"- **Q1 / Q3:** {s.get('q1')} / {s.get('q3')}",
                ]
            else:
                top = s.get("top_values", [])
                if top:
                    tv = ", ".join(f"{v['value']} ({v['count']})" for v in top)
                    lines.append(f"- **Top values:** {tv}")
            lines.append("")
        if self.examples:
            lines += ["## Example Rows", ""]
            headers = list(self.examples[0].keys())
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in self.examples:
                cells = [str(row.get(h, "")) for h in headers]
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
        lines += [
            "## Dataset Statistics", "",
            "| Field | Type | Missing | Unique |",
            "|-------|------|---------|--------|",
        ]
        for fi in self.fields:
            s = fi.stats
            lines.append(
                f"| {fi.name} | {fi.dtype} | {s.get('missing_pct', 0):.1f}% | {s.get('unique', '?')} |"
            )
        lines += [
            "",
            "## License", "",
            f"This dataset is released under the **{self.license}** license.",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class DatacardGenerator:
    """Generate :class:`DataCard` objects from CSV, JSON, or Python data."""

    def __init__(
        self,
        name: str = "My Dataset",
        description: str = "A dataset.",
        license: str = "cc-by-4.0",
        source: str = "",
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
        num_examples: int = 5,
    ) -> None:
        self.name = name
        self.description = description
        self.license = license
        self.source = source
        self.tags = tags or []
        self.version = version
        self.num_examples = num_examples

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

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
        examples = rows[: self.num_examples] if self.num_examples > 0 else []
        return DataCard(
            name=self.name, description=self.description,
            num_rows=len(rows), num_cols=len(columns),
            fields=fields, license=self.license, source=self.source,
            tags=self.tags, version=self.version, examples=examples,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_from_csv(self, path: Path) -> DataCard:
        """Read a CSV file and return a :class:`DataCard`."""
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_json(self, path: Path) -> DataCard:
        """Read a JSON file (array of objects or column dict) and return a :class:`DataCard`."""
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            rows = [
                {k: str(v) for k, v in (r.items() if isinstance(r, dict) else {str(i): str(r)}.items())}
                for i, r in enumerate(data)
            ]
        elif isinstance(data, dict):
            keys = list(data.keys())
            if not keys:
                return self._build_card([])
            n = len(data[keys[0]])
            rows = [{k: str(data[k][i]) for k in keys} for i in range(n)]
        else:
            raise ValueError("JSON must be an array of objects or a column-oriented mapping.")
        return self._build_card(rows)

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        """Accept a list of dicts (as from ``csv.DictReader``) and return a :class:`DataCard`."""
        return self._build_card([{k: str(v) for k, v in row.items()} for row in data])

    def generate(self, source: Any) -> DataCard:
        """Dispatch to the appropriate loader based on *source* type or file extension."""
        if isinstance(source, Path):
            suffix = source.suffix.lower()
            if suffix == ".json":
                return self.generate_from_json(source)
            if suffix in (".parquet", ".arrow"):
                return self._generate_from_columnar(source)
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

    def _generate_from_columnar(self, path: Path) -> DataCard:
        try:
            import pyarrow.parquet as pq  # type: ignore
            table = pq.read_table(path)
            col_dict = table.to_pydict()
            keys = list(col_dict.keys())
            n = len(col_dict[keys[0]]) if keys else 0
            rows = [{k: str(col_dict[k][i]) for k in keys} for i in range(n)]
            return self._build_card(rows)
        except ImportError:
            raise ImportError(
                "Reading Parquet/Arrow files requires pyarrow. "
                "Install it with: pip install pyarrow"
            )
