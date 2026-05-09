#!/usr/bin/env python3
"""
datacard_gen.py — Automated Dataset Datacard Generator

Generates Hugging Face-compatible dataset datacards from CSV files or
in-memory data structures.  Stdlib-only; no external dependencies required.

Typical usage::

    # CLI
    python datacard_gen.py data.csv --name "My Dataset" --format markdown

    # Python API
    from datacard_gen import DatacardGenerator
    gen = DatacardGenerator(name="Iris", license="cc-by-4.0")
    card = gen.generate_from_csv(Path("iris.csv"))
    print(card.to_markdown())
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Statistics helpers ────────────────────────────────────────────────────── #

def _safe_float(v: Any) -> Optional[float]:
    """Return float(v) or None if conversion fails."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[str]) -> bool:
    """Return True when ≥ 80 % of non-empty *values* parse as floats."""
    non_empty = [v for v in values if str(v).strip()]
    if not non_empty:
        return False
    return sum(1 for v in non_empty if _safe_float(v) is not None) / len(non_empty) >= 0.8


def _field_stats(values: List[str]) -> Dict[str, Any]:
    """Compute descriptive statistics for a single column of string values."""
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


# ── Data models ───────────────────────────────────────────────────────────── #

@dataclass
class FieldInfo:
    """Metadata and statistics for a single dataset field (column)."""

    name: str
    dtype: str
    stats: Dict[str, Any]

    def to_dict(self) -> dict:
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


@dataclass
class DataCard:
    """Structured representation of a dataset documentation card."""

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
        """Serialise the card to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render the card as a Hugging Face-compatible Markdown datacard."""
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
                    tv = ", ".join("{} ({})".format(v["value"], v["count"]) for v in top)
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


# ── Generator ─────────────────────────────────────────────────────────────── #

class DatacardGenerator:
    """Builds :class:`DataCard` objects from CSV files or in-memory data."""

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

    def _build_card(self, rows: List[Dict[str, str]]) -> DataCard:
        if not rows:
            return DataCard(
                name=self.name, description=self.description, num_rows=0, num_cols=0,
                license=self.license, source=self.source, tags=self.tags, version=self.version,
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
            license=self.license, source=self.source, tags=self.tags, version=self.version,
        )

    def generate_from_csv(self, path: Path) -> DataCard:
        """Generate a :class:`DataCard` from a CSV file on disk."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"CSV file not found: {path}")
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_string(self, csv_text: str) -> DataCard:
        """Generate a :class:`DataCard` from a CSV string."""
        rows = [dict(r) for r in csv.DictReader(io.StringIO(csv_text))]
        return self._build_card(rows)

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        """Generate a :class:`DataCard` from a list of row dicts."""
        return self._build_card([{k: str(v) for k, v in row.items()} for row in data])

    def generate(self, source: Any) -> DataCard:
        """Generate a :class:`DataCard` from *source*.

        *source* may be:

        - a :class:`~pathlib.Path` or ``str`` path → CSV file on disk
        - a ``list`` of row dicts → :meth:`generate_from_dict`
        - a column-oriented ``dict`` mapping column names to value lists
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


# ── CLI ───────────────────────────────────────────────────────────────────── #

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate Hugging Face-compatible dataset datacards from CSV files.",
    )
    p.add_argument("csv", nargs="?", help="Input CSV file (omit to read from stdin).")
    p.add_argument("--name", default=None, help="Dataset name (defaults to filename stem).")
    p.add_argument("--description", default="A dataset generated automatically.")
    p.add_argument("--license", default="cc-by-4.0")
    p.add_argument("--source", default="", help="Source URL or citation.")
    p.add_argument("--tags", default="", help="Comma-separated list of tags.")
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.add_argument("--output", "-o", help="Write output to this file instead of stdout.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    """CLI entry point. Returns an exit code."""
    args = _parse_args(argv)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    if args.csv:
        path = Path(args.csv)
        if not path.is_file():
            print(f"Error: file not found: {args.csv}", file=sys.stderr)
            return 1
        gen = DatacardGenerator(
            name=args.name or path.stem,
            description=args.description,
            license=args.license,
            source=args.source,
            tags=tags,
            version=args.version,
        )
        card = gen.generate_from_csv(path)
    else:
        raw = sys.stdin.read()
        gen = DatacardGenerator(
            name=args.name or "dataset",
            description=args.description,
            license=args.license,
            source=args.source,
            tags=tags,
            version=args.version,
        )
        card = gen.generate_from_string(raw)

    output = card.to_json() if args.format == "json" else card.to_markdown()
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Datacard written to {args.output}")
    else:
        print(output)
    return 0


# Alias kept for backward compatibility with the pyproject.toml entry point.
_cli = main


if __name__ == "__main__":
    sys.exit(main())
