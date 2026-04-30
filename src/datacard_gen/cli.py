from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

from .generator import DatacardGenerator


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="datacard-gen",
        description="Generate dataset datacards from CSV or JSON files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  datacard-gen dataset.csv -o README.md\n"
            "  datacard-gen dataset.json --name MyData --tags nlp,text --validate\n"
            "  cat data.csv | datacard-gen --name PipedData --format json\n"
        ),
    )
    p.add_argument("file", nargs="?", help="Input CSV or JSON file (default: read CSV from stdin).")
    p.add_argument("--name", default=None, help="Dataset name (default: filename stem).")
    p.add_argument("--description", default="A dataset generated automatically.",
                   help="Dataset description.")
    p.add_argument("--license", default="cc-by-4.0", help="SPDX license identifier (default: cc-by-4.0).")
    p.add_argument("--source", default="", help="Dataset provenance URL or description.")
    p.add_argument("--tags", default="", help="Comma-separated Hugging Face Hub tags.")
    p.add_argument("--version", default="1.0.0", help="Dataset version (default: 1.0.0).")
    p.add_argument(
        "--format", choices=["markdown", "json"], default="markdown",
        help="Output format (default: markdown).",
    )
    p.add_argument(
        "--validate", action="store_true",
        help="Validate the generated card and print warnings/errors to stderr.",
    )
    p.add_argument("--output", "-o", help="Write output to FILE instead of stdout.")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    if args.file:
        path = Path(args.file)
        if not path.is_file():
            print(f"Error: file not found: {args.file}", file=sys.stderr)
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

    if args.validate:
        from .schema import DatacardSchema
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


# Alias so both `datacard_gen.cli:main` and `datacard_gen.cli:cli` work as entry points.
cli = main
