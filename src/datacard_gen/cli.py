"""Command-line interface for datacard-gen."""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path
from typing import List, Optional

from .generator import DatacardGenerator
from .schema import DatacardSchema


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate dataset datacards from CSV files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  datacard-gen dataset.csv
  datacard-gen dataset.csv --name "My Dataset" --format json -o card.json
  cat dataset.csv | datacard-gen --name "Piped Data"
  datacard-gen --gui
""",
    )
    p.add_argument("csv", nargs="?", help="Input CSV file (default: stdin).")
    p.add_argument("--name", default=None, help="Dataset name (default: file stem).")
    p.add_argument("--description", default="A dataset generated automatically.",
                   help="Short description of the dataset.")
    p.add_argument("--license", default="cc-by-4.0",
                   help="SPDX license identifier (default: cc-by-4.0).")
    p.add_argument("--source", default="", help="Dataset source URL or path.")
    p.add_argument("--tags", default="", help="Comma-separated list of tags.")
    p.add_argument("--version", default="1.0.0", help="Dataset version string.")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown",
                   help="Output format (default: markdown).")
    p.add_argument("--output", "-o", metavar="FILE",
                   help="Write output to FILE instead of stdout.")
    p.add_argument("--validate", action="store_true",
                   help="Validate the generated datacard against the schema.")
    p.add_argument("--gui", action="store_true",
                   help="Launch the graphical user interface.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    if args.gui:
        from .gui import launch_gui
        launch_gui()
        return 0

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
        if sys.stdin.isatty():
            print(
                "Error: no input file given and stdin is a terminal.\n"
                "Usage: datacard-gen <file.csv>  or  cat data.csv | datacard-gen",
                file=sys.stderr,
            )
            return 1
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

    if args.validate:
        for warning in DatacardSchema.validate(card.to_dict()):
            print(f"Warning: {warning}", file=sys.stderr)

    output = card.to_json() if args.format == "json" else card.to_markdown()
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Datacard written to {args.output}")
    else:
        print(output)
    return 0
