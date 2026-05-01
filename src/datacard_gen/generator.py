"""Core datacard generation logic."""
from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[str]) -> bool:
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return False
    return sum(1 for v in non_empty if _safe_float(v) is not None) / len(non_empty) >= 0.8


def _field_stats(values: List[str]) -> Dict[str, Any]:
    non_empty = [v for v in values if v.strip()]
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
            stats["type"] = "numeric"
            stats["min"] = nums[0]
            stats["max"] = nums[-1]
            stats["mean"] = round(mean, 4)
            stats["std"] = round(math.sqrt(sum((x - mean) ** 2 for x in nums) / n), 4)
            mid = n // 2
            stats["median"] = nums[mid] if n % 2 else (nums[mid - 1] + nums[mid]) / 2
    else:
        stats["type"] = "categorical"
        freq: Dict[str, int] = {}
        for v in non_empty:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        stats["top_values"] = [{"value": k, "count": v} for k, v in top]
    return stats


@dataclass
class FieldInfo:
    name: str
    dtype: str
    stats: Dict[str, Any]

    def to_dict(self) -> dict:
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


@dataclass
class DataCard:
    name: str
    description: str
    num_rows: int
    num_cols: int
    fields: List[FieldInfo] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    license: str = "unknown"
    source: str = ""
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
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

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
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
            "---",
            "",
            f"# {self.name}",
            "",
            "## Dataset Description",
            "",
            self.description,
            "",
            "## Dataset Structure",
            "",
            f"- **Rows:** {self.num_rows:,}",
            f"- **Columns:** {self.num_cols}",
        ]
        if self.source:
            lines.append(f"- **Source:** {self.source}")
        lines += ["", "## Data Fields", ""]
        for fi in self.fields:
            s = fi.stats
            lines += [
                f"### `{fi.name}` ({fi.dtype})",
                "",
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
                ]
            else:
                top = s.get("top_values", [])
                if top:
                    tv = ", ".join(
                        "{} ({})".format(v["value"], v["count"]) for v in top
                    )
                    lines.append(f"- **Top values:** {tv}")
            lines.append("")
        lines += [
            "## Dataset Statistics",
            "",
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
            "## License",
            "",
            f"This dataset is released under the **{self.license}** license.",
        ]
        return "\n".join(lines)


class DatacardGenerator:
    """Generate dataset datacards from CSV files or Python data structures."""

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

    def generate_from_csv(self, path: Path) -> DataCard:
        """Generate a DataCard by reading a CSV file from *path*."""
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_string(self, csv_content: str) -> DataCard:
        """Generate a DataCard from a CSV-formatted string."""
        rows = [dict(r) for r in csv.DictReader(io.StringIO(csv_content))]
        return self._build_card(rows)

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        """Generate a DataCard from a list of row dicts."""
        return self._build_card([{k: str(v) for k, v in row.items()} for row in data])

    def generate(self, source: Any) -> DataCard:
        """Generate a DataCard from a CSV path, list of row-dicts, or column-oriented dict."""
        if isinstance(source, Path):
            return self.generate_from_csv(source)
        if isinstance(source, list):
            return self.generate_from_dict(source)
        if isinstance(source, dict):
            keys = list(source.keys())
            if not keys:
                return self._build_card([])
            n = len(source[keys[0]])
            return self._build_card(
                [{k: str(source[k][i]) for k in keys} for i in range(n)]
            )
        raise TypeError(f"Unsupported source type: {type(source)}")
