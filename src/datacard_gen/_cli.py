"""Command-line interface for datacard-gen."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from .generator import DatacardGenerator


def _parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description=(
            "Generate Hugging Face-compatible dataset datacards from CSV or JSON files.\n\n"
            "Examples:\n"
            "  datacard-gen dataset.csv -o README.md\n"
            "  datacard-gen dataset.json --format json\n"
            "  cat data.csv | datacard-gen --name MyData\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "input", nargs="?",
        help="Input dataset file (.csv or .json). Reads CSV from stdin when omitted.",
    )
    p.add_argument("--name", default=None, help="Dataset name (defaults to filename stem).")
    p.add_argument("--description", default="A dataset generated automatically.",
                   help="Short description of the dataset.")
    p.add_argument("--license", default="cc-by-4.0",
                   help="SPDX licence identifier (default: cc-by-4.0).")
    p.add_argument("--source", default="", help="Source URL or reference string.")
    p.add_argument("--tags", default="", help="Comma-separated tags.")
    p.add_argument("--version", default="1.0.0", help="Semantic version string (default: 1.0.0).")
    p.add_argument("--examples", type=int, default=5, metavar="N",
                   help="Number of example rows to embed in the card (default: 5).")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown",
                   help="Output format (default: markdown).")
    p.add_argument("--output", "-o", metavar="FILE",
                   help="Write output to FILE instead of stdout.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    gen_kwargs = dict(
        description=args.description,
        license=args.license,
        source=args.source,
        tags=tags,
        version=args.version,
        num_examples=args.examples,
    )

    if args.input:
        path = Path(args.input)
        if not path.is_file():
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            return 1
        gen = DatacardGenerator(name=args.name or path.stem, **gen_kwargs)
        try:
            card = gen.generate(path)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    else:
        raw = sys.stdin.read()
        rows = [dict(r) for r in csv.DictReader(io.StringIO(raw))]
        gen = DatacardGenerator(name=args.name or "dataset", **gen_kwargs)
        card = gen.generate_from_dict(rows)

    output = card.to_json() if args.format == "json" else card.to_markdown()
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Datacard written to {args.output}")
    else:
        print(output)
    return 0
