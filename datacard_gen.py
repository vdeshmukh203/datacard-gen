#!/usr/bin/env python3
"""
datacard_gen — Automated Dataset Datacard Generator

Generates Hugging Face-compatible dataset datacards from CSV files or Python
dicts following the *Datasheets for Datasets* framework (Gebru et al., 2021).
Stdlib-only; no external dependencies required.
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


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    """Return ``float(v)`` or ``None`` if conversion fails."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_numeric(values: List[str]) -> bool:
    """Return True when ≥80 % of non-empty *values* parse as floats."""
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return False
    return sum(1 for v in non_empty if _safe_float(v) is not None) / len(non_empty) >= 0.8


def _field_stats(values: List[str]) -> Dict[str, Any]:
    """Compute summary statistics for a list of raw string values.

    Returns a dict containing ``count``, ``missing``, ``missing_pct``,
    ``unique``, ``type`` (``"numeric"`` or ``"categorical"``), and
    type-specific keys (``min``/``max``/``mean``/``std``/``median`` for
    numeric, ``top_values`` for categorical).
    """
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
            variance = sum((x - mean) ** 2 for x in nums) / n  # population std
            stats["type"] = "numeric"
            stats["min"] = nums[0]
            stats["max"] = nums[-1]
            stats["mean"] = round(mean, 4)
            stats["std"] = round(math.sqrt(variance), 4)
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


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FieldInfo:
    """Summary information for one dataset column."""

    name: str
    dtype: str  # "numeric" or "categorical"
    stats: Dict[str, Any]

    def to_dict(self) -> dict:
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


@dataclass
class DataCard:
    """A complete dataset documentation card.

    Attributes
    ----------
    name:        Human-readable dataset name.
    description: Short dataset description.
    num_rows:    Total row count.
    num_cols:    Total column count.
    fields:      Per-column :class:`FieldInfo` objects.
    tags:        Free-text tags (Hugging Face compatible).
    license:     SPDX license identifier (e.g. ``"cc-by-4.0"``).
    source:      Origin URL or citation string.
    version:     Dataset version string.
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

    def to_dict(self) -> dict:
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
        """Render a Hugging Face-compatible Markdown dataset card.

        The output includes a YAML frontmatter block followed by sections
        modelled on the *Datasheets for Datasets* framework:
        Motivation, Composition, Collection Process, Uses, Distribution,
        and Maintenance.
        """
        lines: List[str] = []

        # --- YAML frontmatter ---
        lines += ["---", f"pretty_name: {self.name}", f"license: {self.license}", f"version: {self.version}"]
        if self.tags:
            lines.append("tags:")
            for t in self.tags:
                lines.append(f"  - {t}")
        lines.append("---")
        lines.append("")

        # --- Title & summary ---
        lines += [f"# {self.name}", "", "## Dataset Summary", "", self.description, ""]

        # --- Motivation (Datasheets §1) ---
        lines += [
            "## Motivation",
            "",
            "<!-- Why was this dataset created? Who funded / sponsored its creation? -->",
            "",
            "> *Describe the purpose of this dataset and its intended use cases.*",
            "",
        ]

        # --- Composition (Datasheets §2) ---
        lines += [
            "## Composition",
            "",
            f"- **Rows:** {self.num_rows:,}",
            f"- **Columns:** {self.num_cols}",
        ]
        if self.source:
            lines.append(f"- **Source:** {self.source}")
        lines += [
            "",
            "<!-- Does the dataset contain all possible instances or is it a sample? "
            "Is there a label or target variable? -->",
            "",
        ]

        # --- Collection Process (Datasheets §3) ---
        lines += [
            "## Collection Process",
            "",
            "<!-- How was the data collected? Who collected the data and on whose behalf? "
            "Over what timeframe? -->",
            "",
            "> *Describe the collection methodology, instruments, and any sampling strategy.*",
            "",
        ]

        # --- Preprocessing (Datasheets §4) ---
        lines += [
            "## Preprocessing / Cleaning / Labelling",
            "",
            "<!-- Was any preprocessing/cleaning/labeling of the data done? "
            "Was the raw data saved in addition to the processed data? -->",
            "",
            "> *Document any transformations applied to the raw data.*",
            "",
        ]

        # --- Data Fields ---
        lines += ["## Data Fields", ""]
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
                    f"- **Std (population):** {s.get('std')}",
                    f"- **Median:** {s.get('median')}",
                ]
            else:
                top = s.get("top_values", [])
                if top:
                    tv = ", ".join("{} ({})".format(v["value"], v["count"]) for v in top)
                    lines.append(f"- **Top values:** {tv}")
            lines.append("")

        # --- Dataset Statistics summary table ---
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
        lines.append("")

        # --- Uses (Datasheets §5) ---
        lines += [
            "## Uses",
            "",
            "<!-- What (other) tasks could the dataset be used for? "
            "Is there anything the dataset should NOT be used for? -->",
            "",
            "### Intended Uses",
            "",
            "> *List the primary tasks and domains this dataset supports.*",
            "",
            "### Out-of-Scope Uses",
            "",
            "> *List any uses that would be inappropriate or harmful.*",
            "",
        ]

        # --- Distribution (Datasheets §6) ---
        lines += [
            "## Distribution",
            "",
            f"This dataset is released under the **{self.license}** license.",
            "",
            "<!-- How is the dataset distributed? "
            "Are there any export controls or other regulatory restrictions? -->",
            "",
        ]

        # --- Maintenance (Datasheets §7) ---
        lines += [
            "## Maintenance",
            "",
            "<!-- Who will be maintaining/hosting/archiving the dataset? "
            "How can the owner/curator/manager of the dataset be contacted? -->",
            "",
            "> *Describe the maintenance plan, versioning policy, and point of contact.*",
            "",
        ]

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class DatacardGenerator:
    """Profile a dataset and produce a :class:`DataCard`.

    Parameters
    ----------
    name:        Dataset name (used in card header and YAML frontmatter).
    description: Short free-text description.
    license:     SPDX identifier, e.g. ``"cc-by-4.0"`` or ``"mit"``.
    source:      Provenance URL or citation string.
    tags:        List of Hugging Face-compatible tag strings.
    version:     Semantic version string.

    Examples
    --------
    >>> gen = DatacardGenerator(name="Iris", license="cc0-1.0")
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
        """Read *path* as a CSV file and return a :class:`DataCard`."""
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_dict(self, data: List[Dict[str, Any]]) -> DataCard:
        """Build a :class:`DataCard` from a list of dicts (one dict per row)."""
        return self._build_card([{k: str(v) for k, v in row.items()} for row in data])

    def generate(self, source) -> DataCard:
        """Polymorphic entry point.

        Accepts:
        - :class:`pathlib.Path` — read as CSV.
        - ``list`` of dicts — each dict is one row.
        - ``dict`` of lists — column-oriented layout ``{col: [values...]}``.
        """
        if isinstance(source, Path):
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate Hugging Face-compatible dataset datacards from CSV files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  datacard-gen dataset.csv --name 'My Dataset' --license cc-by-4.0\n"
            "  datacard-gen dataset.csv --format json -o card.json\n"
            "  cat data.csv | datacard-gen --name 'Piped Dataset'\n"
            "  datacard-gen --gui"
        ),
    )
    p.add_argument("csv", nargs="?", help="Input CSV file (omit to read from stdin).")
    p.add_argument("--name", default=None, help="Dataset name.")
    p.add_argument("--description", default="A dataset generated automatically.", help="Short description.")
    p.add_argument("--license", default="cc-by-4.0", help="SPDX license identifier (default: cc-by-4.0).")
    p.add_argument("--source", default="", help="Provenance URL or citation.")
    p.add_argument("--tags", default="", help="Comma-separated Hugging Face tags.")
    p.add_argument("--version", default="1.0.0", help="Dataset version string.")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format.")
    p.add_argument("--output", "-o", metavar="FILE", help="Write output to FILE instead of stdout.")
    p.add_argument("--gui", action="store_true", help="Launch the graphical user interface.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    """CLI entry point; returns an exit code."""
    args = _parse_args(argv)

    if args.gui:
        try:
            from datacard_gen_gui import main as gui_main
            gui_main()
            return 0
        except ImportError:
            print("Error: datacard_gen_gui.py not found. Install the package to use the GUI.", file=sys.stderr)
            return 1

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


# Keep this alias so existing entry points referencing `_cli` keep working.
_cli = main


if __name__ == "__main__":
    sys.exit(main())
