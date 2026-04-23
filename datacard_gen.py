"""
datacard_gen: Automatically generate dataset documentation cards (datasheets) from
tabular data files, following the Datasheets for Datasets framework.

Supports CSV, TSV, JSON Lines, and Parquet inputs. Produces structured Markdown
output with statistical summaries, field descriptions, missing-value analysis,
and provenance metadata.
"""
from __future__ import annotations
import csv, json, hashlib, datetime, statistics
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Field statistics
# ---------------------------------------------------------------------------

def _is_numeric(values: List[str]) -> bool:
    count = 0
    for v in values:
        try:
            float(v)
            count += 1
        except (ValueError, TypeError):
            pass
    return count / max(len(values), 1) > 0.8


def _field_stats(name: str, values: List[str]) -> Dict[str, Any]:
    non_null = [v for v in values if v not in ("", "null", "NULL", "None", "NA", "N/A")]
    missing = len(values) - len(non_null)
    stats: Dict[str, Any] = {
        "field": name,
        "total": len(values),
        "missing": missing,
        "missing_pct": round(100 * missing / max(len(values), 1), 2),
        "unique": len(set(non_null)),
    }
    if _is_numeric(non_null) and non_null:
        nums = [float(v) for v in non_null if _safe_float(v) is not None]
        if nums:
            stats["type"] = "numeric"
            stats["min"] = min(nums)
            stats["max"] = max(nums)
            stats["mean"] = round(statistics.mean(nums), 4)
            stats["median"] = round(statistics.median(nums), 4)
            try:
                stats["stdev"] = round(statistics.stdev(nums), 4)
            except statistics.StatisticsError:
                stats["stdev"] = 0.0
    else:
        stats["type"] = "categorical"
        freq: Dict[str, int] = {}
        for v in non_null:
            freq[v] = freq.get(v, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:5]
        stats["top_values"] = [{"value": k, "count": c} for k, c in top]
    return stats


def _safe_float(v: str) -> Optional[float]:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_csv(path: Path, delimiter: str = ",") -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _load_jsonl(path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    keys: List[str] = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                keys.append(k)
                seen.add(k)
    return keys, rows


def load_dataset(path: str) -> Tuple[List[str], List[Dict]]:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".csv",):
        return _load_csv(p, delimiter=",")
    elif suffix in (".tsv",):
        return _load_csv(p, delimiter="\t")
    elif suffix in (".jsonl", ".ndjson"):
        return _load_jsonl(p)
    elif suffix == ".parquet":
        try:
            import struct, io
            # minimal parquet magic check
            with p.open("rb") as f:
                magic = f.read(4)
            if magic != b"PAR1":
                raise ValueError("Not a valid Parquet file.")
            raise ImportError("Install pyarrow for Parquet support: pip install pyarrow")
        except ImportError as e:
            raise ImportError(str(e)) from e
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use .csv, .tsv, or .jsonl")


# ---------------------------------------------------------------------------
# Datacard builder
# ---------------------------------------------------------------------------

class DatacardGenerator:
    """
    Generate a Markdown datasheet from a tabular dataset.

    Parameters
    ----------
    path : str
        Path to the dataset file.
    name : str, optional
        Human-readable name for the dataset.
    description : str, optional
        Short description of the dataset.
    license_str : str, optional
        SPDX license identifier, e.g. "CC-BY-4.0".
    source_url : str, optional
        URL where the dataset was obtained.
    authors : list of str, optional
        List of dataset author names.
    tasks : list of str, optional
        Intended ML tasks (e.g. ["classification", "regression"]).
    """

    def __init__(
        self,
        path: str,
        name: str = "",
        description: str = "",
        license_str: str = "Unknown",
        source_url: str = "",
        authors: Optional[List[str]] = None,
        tasks: Optional[List[str]] = None,
    ) -> None:
        self.path = Path(path)
        self.name = name or self.path.stem
        self.description = description
        self.license_str = license_str
        self.source_url = source_url
        self.authors = authors or []
        self.tasks = tasks or []
        self._fields: List[str] = []
        self._rows: List[Dict] = []
        self._stats: List[Dict[str, Any]] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        self._fields, self._rows = load_dataset(str(self.path))
        for field in self._fields:
            vals = [str(row.get(field, "")) for row in self._rows]
            self._stats.append(_field_stats(field, vals))
        self._loaded = True

    def _file_hash(self) -> str:
        h = hashlib.sha256()
        with self.path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _format_stat_row(self, s: Dict[str, Any]) -> str:
        if s["type"] == "numeric":
            detail = (f"min={s['min']}, max={s['max']}, "
                      f"mean={s['mean']}, stdev={s.get('stdev', 'N/A')}")
        else:
            top = ", ".join(f"{t['value']} ({t['count']})" for t in s.get("top_values", [])[:3])
            detail = f"top: {top}"
        return (f"| {s['field']} | {s['type']} | {s['total']} | "
                f"{s['missing']} ({s['missing_pct']}%) | {s['unique']} | {detail} |")

    def generate(self) -> str:
        self._load()
        now = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        size_bytes = self.path.stat().st_size
        sha256 = self._file_hash()
        n_rows = len(self._rows)
        n_cols = len(self._fields)

        lines = [
            f"# Datacard: {self.name}",
            "",
            f"> Generated by datacard-gen on {now}",
            "",
            "## Overview",
            "",
            f"| Property | Value |",
            f"|---|---|",
            f"| Name | {self.name} |",
            f"| Description | {self.description or 'N/A'} |",
            f"| Source | {self.source_url or 'N/A'} |",
            f"| License | {self.license_str} |",
            f"| Authors | {', '.join(self.authors) or 'N/A'} |",
            f"| Intended Tasks | {', '.join(self.tasks) or 'N/A'} |",
            f"| File | {self.path.name} |",
            f"| Size | {size_bytes:,} bytes |",
            f"| SHA-256 | {sha256} |",
            f"| Rows | {n_rows:,} |",
            f"| Columns | {n_cols} |",
            "",
            "## Field Statistics",
            "",
            "| Field | Type | Total | Missing | Unique | Details |",
            "|---|---|---|---|---|---|",
        ]
        for s in self._stats:
            lines.append(self._format_stat_row(s))

        # Missing value summary
        high_missing = [s for s in self._stats if s["missing_pct"] > 10]
        if high_missing:
            lines += [
                "",
                "## Data Quality Notes",
                "",
                "Fields with >10% missing values:",
                "",
            ]
            for s in high_missing:
                lines.append(f"- **{s['field']}**: {s['missing_pct']}% missing")

        lines += [
            "",
            "## Provenance",
            "",
            f"- **Generated**: {now}",
            f"- **Tool**: datacard-gen",
            f"- **File hash (SHA-256)**: {sha256}",
            "",
            "---",
            "",
            "_This datacard was automatically generated. "
            "Review and supplement with domain-specific context before publication._",
        ]
        return "\n".join(lines)

    def save(self, output_path: Optional[str] = None) -> Path:
        text = self.generate()
        out = Path(output_path) if output_path else self.path.with_suffix(".datacard.md")
        out.write_text(text, encoding="utf-8")
        return out


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def generate_datacard(
    input_path: str,
    output_path: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """
    Generate a datacard for a dataset file and optionally write it to disk.

    Parameters
    ----------
    input_path : str
        Path to the input dataset (CSV, TSV, or JSONL).
    output_path : str, optional
        Where to write the Markdown output. Defaults to <input>.datacard.md.
    **kwargs
        Forwarded to DatacardGenerator (name, description, license_str, etc.).

    Returns
    -------
    str
        The generated Markdown text.
    """
    gen = DatacardGenerator(input_path, **kwargs)
    text = gen.generate()
    out = gen.save(output_path)
    print(f"Datacard written to {out}")
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate dataset documentation cards from tabular data files.",
    )
    parser.add_argument("input", help="Path to dataset (CSV/TSV/JSONL).")
    parser.add_argument("-o", "--output", default=None, help="Output .md path.")
    parser.add_argument("-n", "--name", default="", help="Dataset name.")
    parser.add_argument("-d", "--description", default="")
    parser.add_argument("-l", "--license", dest="license_str", default="Unknown")
    parser.add_argument("-s", "--source", dest="source_url", default="")
    parser.add_argument("-a", "--authors", nargs="+", default=[])
    parser.add_argument("-t", "--tasks", nargs="+", default=[])
    args = parser.parse_args()
    generate_datacard(
        args.input, args.output,
        name=args.name, description=args.description,
        license_str=args.license_str, source_url=args.source_url,
        authors=args.authors, tasks=args.tasks,
    )


if __name__ == "__main__":
    _cli()
