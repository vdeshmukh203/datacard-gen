#!/usr/bin/env python3
"""
datacard_gen — Automated Dataset Datacard Generator

Generates Hugging Face-compatible dataset documentation cards from CSV or
JSON files (or in-memory Python dicts/lists).  Stdlib-only; no external
dependencies required for core functionality.
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
from typing import Any, Dict, List, Optional, Union

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    """Return *v* as ``float``, or ``None`` if conversion fails."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[str]) -> bool:
    """Return ``True`` when ≥ 80 % of non-empty *values* parse as floats."""
    non_empty = [v for v in values if str(v).strip()]
    if not non_empty:
        return False
    numeric_count = sum(1 for v in non_empty if _safe_float(v) is not None)
    return numeric_count / len(non_empty) >= 0.8


def _field_stats(values: List[str]) -> Dict[str, Any]:
    """Compute per-field descriptive statistics.

    Parameters
    ----------
    values:
        Raw string values for one column (may include empty strings).

    Returns
    -------
    dict
        Always contains ``count``, ``missing``, ``missing_pct``, ``unique``,
        and ``type`` (``"numeric"`` | ``"categorical"``).  Numeric fields also
        carry ``min``, ``max``, ``mean``, ``std`` (population), and
        ``median``; categorical fields carry ``top_values``.
    """
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
            # Population std — appropriate when the whole dataset is documented.
            variance = sum((x - mean) ** 2 for x in nums) / n
            mid = n // 2
            median = nums[mid] if n % 2 else (nums[mid - 1] + nums[mid]) / 2
            stats.update({
                "type": "numeric",
                "min": nums[0],
                "max": nums[-1],
                "mean": round(mean, 4),
                "std": round(math.sqrt(variance), 4),
                "median": median,
            })
        else:
            stats["type"] = "numeric"
    else:
        freq: Dict[str, int] = {}
        for v in non_empty:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        stats["type"] = "categorical"
        stats["top_values"] = [{"value": k, "count": c} for k, c in top]
    return stats


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FieldInfo:
    """Metadata and statistics for a single dataset column."""

    name: str
    dtype: str
    stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


@dataclass
class DataCard:
    """Complete dataset documentation card.

    Attributes
    ----------
    name:        Human-readable dataset name.
    description: Free-text description of the dataset.
    num_rows:    Total number of rows.
    num_cols:    Total number of columns.
    fields:      Per-column metadata list.
    tags:        Free-form tag list (HF Hub compatible).
    license:     SPDX license identifier (e.g. ``"cc-by-4.0"``).
    source:      URL or citation for the data origin.
    version:     Semantic version string.
    """

    name: str
    description: str
    num_rows: int
    num_cols: int
    fields: List[FieldInfo] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    license: str = "unknown"
    source: str = ""
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain Python ``dict``."""
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
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render as a Hugging Face-compatible Markdown datacard."""
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


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class DatacardGenerator:
    """Profile a dataset and produce a :class:`DataCard`.

    Parameters
    ----------
    name:        Dataset name (defaults to the CSV filename stem).
    description: Free-text description.
    license:     SPDX identifier, e.g. ``"cc-by-4.0"``.
    source:      Provenance URL or citation string.
    tags:        List of HF Hub-style tags.
    version:     Semantic version string.

    Examples
    --------
    >>> gen = DatacardGenerator(name="iris", license="cc0-1.0")
    >>> card = gen.generate(Path("iris.csv"))
    >>> print(card.to_markdown())
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

    # ------------------------------------------------------------------
    # Internal

    def _build_card(self, rows: List[Dict[str, str]]) -> DataCard:
        """Build a :class:`DataCard` from a list of string-valued row dicts."""
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
            values = [str(row.get(col, "")) for row in rows]
            stats = _field_stats(values)
            dtype = stats.pop("type", "categorical")
            fields.append(FieldInfo(name=col, dtype=dtype, stats=stats))
        return DataCard(
            name=self.name, description=self.description,
            num_rows=len(rows), num_cols=len(columns),
            fields=fields,
            license=self.license, source=self.source,
            tags=self.tags, version=self.version,
        )

    # ------------------------------------------------------------------
    # Public loaders

    def generate_from_csv(self, path: Union[Path, str]) -> DataCard:
        """Generate a card from a CSV file on disk.

        Parameters
        ----------
        path: Path to the CSV file.

        Raises
        ------
        FileNotFoundError: If *path* does not exist.
        """
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"CSV file not found: {path}")
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_json(self, path: Union[Path, str]) -> DataCard:
        """Generate a card from a JSON file (array of objects) on disk.

        Parameters
        ----------
        path: Path to the JSON file.

        Raises
        ------
        FileNotFoundError: If *path* does not exist.
        ValueError: If the JSON is not a list of objects.
        """
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"JSON file not found: {path}")
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("JSON input must be an array of objects.")
        return self.generate_from_dict(data)

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        """Generate a card from an in-memory list of row dicts.

        Parameters
        ----------
        data: List of dicts, each representing one row.
        """
        return self._build_card([{k: str(v) for k, v in row.items()} for row in data])

    def generate(
        self, source: Union[Path, str, List[Dict[str, Any]], Dict[str, List[Any]]]
    ) -> DataCard:
        """Dispatch to the appropriate loader based on *source* type.

        Accepted inputs
        ---------------
        * :class:`pathlib.Path` or ``str`` ending in ``.json`` → :meth:`generate_from_json`
        * :class:`pathlib.Path` or ``str`` (any other extension) → :meth:`generate_from_csv`
        * ``list`` of dicts → :meth:`generate_from_dict`
        * ``dict`` of ``{column: [values]}`` (columnar layout) → converted automatically

        Raises
        ------
        TypeError: For unsupported *source* types.
        ValueError: If a columnar dict has columns of unequal length.
        """
        if isinstance(source, (Path, str)):
            p = Path(source)
            if p.suffix.lower() == ".json":
                return self.generate_from_json(p)
            return self.generate_from_csv(p)
        if isinstance(source, list):
            return self.generate_from_dict(source)
        if isinstance(source, dict):
            keys = list(source.keys())
            if not keys:
                return self._build_card([])
            lengths = {k: len(source[k]) for k in keys}
            if len(set(lengths.values())) > 1:
                raise ValueError(
                    "Columnar dict has columns of unequal length: "
                    + ", ".join(f"{k}={v}" for k, v in lengths.items())
                )
            n = lengths[keys[0]]
            rows = [{k: str(source[k][i]) for k in keys} for i in range(n)]
            return self._build_card(rows)
        raise TypeError(f"Unsupported source type: {type(source)!r}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate dataset datacards from CSV or JSON files.",
    )
    p.add_argument("input", nargs="?", help="Input file (CSV or JSON). Reads stdin if omitted.")
    p.add_argument("--name", default=None, help="Dataset name.")
    p.add_argument("--description", default="A dataset generated automatically.")
    p.add_argument("--license", default="cc-by-4.0", help="SPDX license identifier.")
    p.add_argument("--source", default="", help="Provenance URL or citation.")
    p.add_argument("--tags", default="", help="Comma-separated tag list.")
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown",
                   help="Output format (default: markdown).")
    p.add_argument("--output", "-o", metavar="FILE", help="Write output to FILE instead of stdout.")
    p.add_argument("--gui", action="store_true", help="Launch the graphical interface.")
    p.add_argument("--version-info", action="version", version=f"%(prog)s {__version__}")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the ``datacard-gen`` CLI command."""
    args = _parse_args(argv)

    if args.gui:
        try:
            from datacard_gui import main as gui_main
            gui_main()
            return 0
        except ImportError:
            print("GUI module not found. Install tkinter or run datacard-gen-gui.", file=sys.stderr)
            return 1

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    if args.input:
        path = Path(args.input)
        if not path.is_file():
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            return 1
        gen = DatacardGenerator(
            name=args.name or path.stem,
            description=args.description,
            license=args.license,
            source=args.source,
            tags=tags,
            version=args.version,
        )
        try:
            card = gen.generate(path)
        except (ValueError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    else:
        raw = sys.stdin.read()
        rows = [dict(r) for r in csv.DictReader(io.StringIO(raw))]
        gen = DatacardGenerator(
            name=args.name or "dataset",
            description=args.description,
            license=args.license,
            source=args.source,
            tags=tags,
            version=args.version,
        )
        card = gen.generate_from_dict(rows)

    output = card.to_json() if args.format == "json" else card.to_markdown()

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Datacard written to {args.output}")
    else:
        print(output)
    return 0


# Alias expected by pyproject.toml entry-point
_cli = main


if __name__ == "__main__":
    sys.exit(main())
