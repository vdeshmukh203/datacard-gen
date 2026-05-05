#!/usr/bin/env python3
"""
datacard_gen — Automated Dataset Datacard Generator
====================================================
Generates Hugging Face-compatible dataset documentation cards from CSV or
JSON files, or from in-memory Python dicts/lists.  Requires only the Python
standard library (≥ 3.8).

Public API
----------
DatacardGenerator
    Main class — instantiate with dataset metadata, then call
    :meth:`generate`, :meth:`generate_from_csv`, or
    :meth:`generate_from_json`.

DataCard
    Result dataclass with :meth:`to_markdown` / :meth:`to_json`.

FieldInfo
    Per-column metadata attached to a :class:`DataCard`.
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


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    """Return *v* coerced to :class:`float`, or ``None`` on failure."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[Any]) -> bool:
    """Return ``True`` when ≥ 80 % of non-empty *values* convert to float."""
    non_empty = [v for v in values if str(v).strip()]
    if not non_empty:
        return False
    return (
        sum(1 for v in non_empty if _safe_float(v) is not None) / len(non_empty)
        >= 0.8
    )


def _field_stats(values: List[Any]) -> Dict[str, Any]:
    """Compute descriptive statistics for one column of raw values.

    Parameters
    ----------
    values:
        All values (including missing) for a single column.

    Returns
    -------
    dict
        Keys always present: ``count``, ``missing``, ``missing_pct``,
        ``unique``, ``type`` (``"numeric"`` | ``"categorical"``).

        Numeric columns also include: ``min``, ``max``, ``mean``, ``std``
        (population), ``median``.

        Categorical columns also include: ``top_values`` — up to five
        most-frequent values with their counts.
    """
    str_vals = [str(v) for v in values]
    non_empty = [v for v in str_vals if v.strip()]
    total = len(str_vals)
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
            variance = sum((x - mean) ** 2 for x in nums) / n
            mid = n // 2
            median = nums[mid] if n % 2 else (nums[mid - 1] + nums[mid]) / 2
            stats.update({
                "type": "numeric",
                "min": nums[0],
                "max": nums[-1],
                "mean": round(mean, 4),
                "std": round(math.sqrt(variance), 4),
                "median": round(median, 4),
            })
    else:
        freq: Dict[str, int] = {}
        for v in non_empty:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        stats.update({
            "type": "categorical",
            "top_values": [{"value": k, "count": cnt} for k, cnt in top],
        })
    return stats


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------

@dataclass
class FieldInfo:
    """Metadata and statistics for a single dataset column."""

    name: str
    dtype: str
    stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable dict representation."""
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


@dataclass
class DataCard:
    """Complete documentation card for a dataset."""

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
        """Return a JSON-serialisable dict representation."""
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
        """Render the card as a Hugging Face-compatible Markdown string.

        The output begins with a YAML frontmatter block (``---`` … ``---``)
        recognised by the Hugging Face Hub, followed by Markdown sections for
        description, dataset structure, per-field statistics, a summary table,
        and the licence.
        """
        lines: List[str] = [
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
                        f"{v['value']} ({v['count']})" for v in top
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
    """Generate :class:`DataCard` objects from various dataset sources.

    Parameters
    ----------
    name:
        Human-readable dataset name.
    description:
        Short plain-text description of the dataset.
    license:
        SPDX licence identifier (e.g. ``"cc-by-4.0"``).
    source:
        URL or citation string identifying where the dataset originates.
    tags:
        List of free-text tags (task category, domain, language, …).
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

    def _build_card(self, rows: List[Dict[str, Any]]) -> DataCard:
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

    def generate_from_csv(self, path: Union[str, Path]) -> DataCard:
        """Load a CSV file and return a :class:`DataCard`.

        Parameters
        ----------
        path:
            Path to a UTF-8-encoded CSV file.
        """
        rows: List[Dict[str, str]] = []
        with Path(path).open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_json(self, path: Union[str, Path]) -> DataCard:
        """Load a JSON file and return a :class:`DataCard`.

        Accepted formats:

        * **Row-oriented** — a JSON array of objects:
          ``[{"col": val, …}, …]``
        * **Column-oriented** — an object of equal-length arrays:
          ``{"col": [v1, v2, …], …}``

        Parameters
        ----------
        path:
            Path to a UTF-8-encoded JSON file.
        """
        with Path(path).open(encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return self.generate_from_dict(data)
        if isinstance(data, dict):
            return self.generate(data)
        raise ValueError(
            "JSON file must contain either an array of objects or an object of arrays."
        )

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        """Build a :class:`DataCard` from a list of row dicts.

        Parameters
        ----------
        data:
            List of dicts where each dict represents one row; values are
            coerced to strings before profiling.
        """
        return self._build_card(
            [{k: str(v) for k, v in row.items()} for row in data]
        )

    def generate(
        self,
        source: Union[Path, str, List[Dict[str, Any]], Dict[str, Any]],
    ) -> DataCard:
        """Universal entry point — dispatch based on the type of *source*.

        Parameters
        ----------
        source:
            * :class:`pathlib.Path` or :class:`str` — path to a CSV or JSON
              file (detected by ``.json`` extension).
            * :class:`list` — list of row dicts (forwarded to
              :meth:`generate_from_dict`).
            * :class:`dict` — column-oriented dict mapping column names to
              equal-length value lists.
        """
        if isinstance(source, (str, Path)):
            p = Path(source)
            if not p.is_file():
                raise FileNotFoundError(f"Dataset file not found: {p}")
            if p.suffix.lower() == ".json":
                return self.generate_from_json(p)
            return self.generate_from_csv(p)
        if isinstance(source, list):
            return self.generate_from_dict(source)
        if isinstance(source, dict):
            keys = list(source.keys())
            if not keys:
                return self._build_card([])
            lengths = {len(v) for v in source.values()}
            if len(lengths) != 1:
                raise ValueError(
                    "Column-oriented dict must have equal-length arrays for all columns."
                )
            n = lengths.pop()
            return self._build_card(
                [{k: str(source[k][i]) for k in keys} for i in range(n)]
            )
        raise TypeError(f"Unsupported source type: {type(source)!r}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate dataset datacards from CSV or JSON files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "input",
        nargs="?",
        metavar="FILE",
        help="Input CSV or JSON file (reads from stdin if omitted).",
    )
    p.add_argument("--name", default=None, help="Dataset name.")
    p.add_argument(
        "--description",
        default="A dataset generated automatically.",
        help="Short dataset description.",
    )
    p.add_argument("--license", default="cc-by-4.0", help="SPDX licence identifier.")
    p.add_argument("--source", default="", help="Dataset source URL or citation.")
    p.add_argument("--tags", default="", help="Comma-separated list of tags.")
    p.add_argument("--version", default="1.0.0", help="Dataset version string.")
    p.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format.",
    )
    p.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.  Returns exit code 0 on success, 1 on error."""
    args = _parse_args(argv)
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
        card = gen.generate(path)
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


# Alias used by the pyproject.toml console-script entry-point declaration.
_cli = main


if __name__ == "__main__":
    sys.exit(main())
