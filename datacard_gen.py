#!/usr/bin/env python3
"""
datacard_gen.py — Automated Dataset Datacard Generator
Generates Hugging Face-compatible dataset datacards from CSV or JSON files.
Stdlib-only. No external dependencies.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import sys
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
            stats["std"] = round(math.sqrt(sum((x - mean)**2 for x in nums) / n), 4)
            mid = n // 2
            stats["median"] = nums[mid] if n % 2 else (nums[mid-1] + nums[mid]) / 2
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
            "name": self.name, "description": self.description,
            "num_rows": self.num_rows, "num_cols": self.num_cols,
            "license": self.license, "source": self.source,
            "version": self.version, "tags": self.tags,
            "fields": [f.to_dict() for f in self.fields],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        lines = ["---", f"pretty_name: {self.name}", f"license: {self.license}", f"version: {self.version}"]
        if self.tags:
            lines.append("tags:")
            for t in self.tags:
                lines.append(f"  - {t}")
        lines += ["---", "", f"# {self.name}", "", "## Dataset Description", "", self.description, "",
                  "## Dataset Structure", "",
                  f"- **Rows:** {self.num_rows:,}", f"- **Columns:** {self.num_cols}"]
        if self.source:
            lines.append(f"- **Source:** {self.source}")
        lines += ["", "## Data Fields", ""]
        for fi in self.fields:
            s = fi.stats
            lines += [
                f"### `{fi.name}` ({fi.dtype})", "",
                f"- **Missing:** {s.get('missing',0)} ({s.get('missing_pct',0):.1f}%)",
                f"- **Unique values:** {s.get('unique','?')}",
            ]
            if fi.dtype == "numeric":
                lines += [
                    f"- **Min:** {s.get('min')}", f"- **Max:** {s.get('max')}",
                    f"- **Mean:** {s.get('mean')}", f"- **Std:** {s.get('std')}",
                    f"- **Median:** {s.get('median')}",
                ]
            else:
                top = s.get("top_values", [])
                if top:
                    tv = ', '.join("{} ({})".format(v['value'], v['count']) for v in top)
                    lines.append(f"- **Top values:** {tv}")
            lines.append("")
        lines += [
            "## Dataset Statistics", "",
            "| Field | Type | Missing | Unique |",
            "|-------|------|---------|--------|",
        ]
        for fi in self.fields:
            s = fi.stats
            lines.append(f"| {fi.name} | {fi.dtype} | {s.get('missing_pct',0):.1f}% | {s.get('unique','?')} |")
        lines += ["", "## License", "", f"This dataset is released under the **{self.license}** license."]
        return "\n".join(lines)


_SPDX_COMMON = {
    "mit", "apache-2.0", "gpl-2.0", "gpl-3.0", "lgpl-2.1", "lgpl-3.0",
    "bsd-2-clause", "bsd-3-clause", "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0",
    "cc-by-nc-4.0", "cc-by-nc-sa-4.0", "cc-by-nd-4.0", "openrail", "unknown",
}
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"Valid: {self.valid}"]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


class DatacardSchema:
    """Validates a DataCard against the Hugging Face dataset card schema."""

    def validate(self, card: "DataCard") -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        if not card.name or not card.name.strip():
            errors.append("'name' is required and must not be empty.")
        if not card.description or card.description.strip() in (
            "", "A dataset.", "A dataset generated automatically."
        ):
            warnings.append("'description' is a placeholder; provide a meaningful description.")
        if not _SEMVER_RE.match(card.version):
            warnings.append(
                f"'version' '{card.version}' does not follow semantic versioning (MAJOR.MINOR.PATCH)."
            )
        if card.license.lower() not in _SPDX_COMMON:
            warnings.append(f"'license' '{card.license}' is not a recognised SPDX identifier.")
        if not card.tags:
            warnings.append("'tags' is empty. Adding tags improves Hub discoverability.")
        if card.num_rows == 0:
            warnings.append("Dataset has zero rows.")
        for fi in card.fields:
            if not fi.name or not fi.name.strip():
                errors.append("A field has an empty name.")
            if fi.dtype not in ("numeric", "categorical"):
                errors.append(f"Field '{fi.name}' has unknown dtype '{fi.dtype}'.")
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


class DatacardGenerator:
    def __init__(self, name: str = "My Dataset", description: str = "A dataset.",
                 license: str = "cc-by-4.0", source: str = "",
                 tags: Optional[List[str]] = None, version: str = "1.0.0"):
        self.name = name
        self.description = description
        self.license = license
        self.source = source
        self.tags = tags or []
        self.version = version

    def _build_card(self, rows: List[Dict[str, str]]) -> DataCard:
        if not rows:
            return DataCard(name=self.name, description=self.description, num_rows=0, num_cols=0,
                            license=self.license, source=self.source, tags=self.tags, version=self.version)
        columns = list(rows[0].keys())
        fields: List[FieldInfo] = []
        for col in columns:
            values = [row.get(col, "") for row in rows]
            stats = _field_stats(values)
            dtype = stats.pop("type", "categorical")
            fields.append(FieldInfo(name=col, dtype=dtype, stats=stats))
        return DataCard(name=self.name, description=self.description,
                        num_rows=len(rows), num_cols=len(columns), fields=fields,
                        license=self.license, source=self.source, tags=self.tags, version=self.version)

    def generate_from_csv(self, path: Path) -> DataCard:
        rows: List[Dict[str, str]] = []
        with path.open(encoding="utf-8", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh):
                rows.append(dict(row))
        return self._build_card(rows)

    def generate_from_json(self, path: Path) -> DataCard:
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

    def generate(self, source) -> DataCard:
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


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate dataset datacards from CSV or JSON files.",
    )
    p.add_argument("file", nargs="?", help="Input CSV or JSON file (default: read CSV from stdin).")
    p.add_argument("--name", default=None)
    p.add_argument("--description", default="A dataset generated automatically.")
    p.add_argument("--license", default="cc-by-4.0")
    p.add_argument("--source", default="")
    p.add_argument("--tags", default="", help="Comma-separated tags.")
    p.add_argument("--version", default="1.0.0")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown",
                   help="Output format (default: markdown).")
    p.add_argument("--validate", action="store_true",
                   help="Validate the generated card and print any warnings/errors.")
    p.add_argument("--output", "-o", help="Write to file instead of stdout.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
            return 1
        gen = DatacardGenerator(name=args.name or path.stem, description=args.description,
                                license=args.license, source=args.source, tags=tags, version=args.version)
        card = gen.generate(path)
    else:
        raw = sys.stdin.read()
        rows = [dict(r) for r in csv.DictReader(io.StringIO(raw))]
        gen = DatacardGenerator(name=args.name or "dataset", description=args.description,
                                license=args.license, source=args.source, tags=tags, version=args.version)
        card = gen.generate_from_dict(rows)
    if args.validate:
        result = DatacardSchema().validate(card)
        print(str(result), file=sys.stderr)
        if not result.valid:
            return 2
    output = card.to_json() if args.format == "json" else card.to_markdown()
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Datacard written to {args.output}")
    else:
        print(output)
    return 0


# Entry-point alias used by pyproject.toml
_cli = main


if __name__ == "__main__":
    sys.exit(main())
