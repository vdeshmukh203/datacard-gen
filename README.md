# datacard-gen

[![CI](https://github.com/vdeshmukh203/datacard-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/vdeshmukh203/datacard-gen/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python ≥ 3.8](https://img.shields.io/badge/python-%E2%89%A53.8-blue.svg)](https://www.python.org/)

**Automated dataset documentation card generator** following the
[Datasheets for Datasets](https://arxiv.org/abs/1803.09010) framework and
the [Hugging Face dataset card](https://huggingface.co/docs/hub/datasets-cards)
schema.

Given a dataset file, `datacard-gen` computes descriptive statistics, detects
column types, estimates missing-value rates, samples example rows, and emits a
Markdown documentation card that can be committed directly to a repository or
uploaded to Hugging Face Hub.

---

## Features

- **Zero required dependencies** — CSV and JSON input work with the Python
  standard library only.
- **Hugging Face-compatible** YAML front-matter (`pretty_name`, `license`,
  `tags`, `version`).
- **Automatic column profiling** — numeric vs categorical detection, min / max /
  mean / std / median / Q1 / Q3 for numeric columns, top-5 value frequencies
  for categorical columns.
- **Missing-value reporting** — count and percentage per column.
- **Example rows** — configurable number of sample rows embedded in the card.
- **Schema validation** via `DatacardSchema` — checks SPDX licence identifiers,
  semantic versioning, required fields, and more.
- **Multiple output formats** — Markdown (default) or JSON.
- **Parquet / Arrow support** — optional, requires `pyarrow`.
- **Graphical user interface** — Tkinter GUI launched with `datacard-gen-gui`.

---

## Installation

```bash
pip install datacard-gen
```

For Parquet / Arrow support:

```bash
pip install "datacard-gen[parquet]"
```

---

## Quick start

### Command-line

```bash
# Generate a Markdown card and print to stdout
datacard-gen dataset.csv

# Save to README.md with metadata
datacard-gen dataset.csv \
  --name "My Dataset" \
  --description "A curated dataset of survey responses." \
  --license cc-by-4.0 \
  --tags nlp,survey \
  --output README.md

# JSON output
datacard-gen dataset.json --format json -o card.json

# Read CSV from stdin
cat data.csv | datacard-gen --name "Piped Dataset"
```

### GUI

```bash
datacard-gen-gui
```

The GUI lets you browse for a file, fill in metadata, preview the generated
card, and save it — all without touching the command line.

### Python API

```python
from pathlib import Path
from datacard_gen import DatacardGenerator, DatacardSchema

gen = DatacardGenerator(
    name="Iris Dataset",
    description="Classic flower morphology dataset.",
    license="cc0-1.0",
    tags=["tabular", "biology"],
)

# From a CSV file
card = gen.generate(Path("iris.csv"))

# From a list of dicts
card = gen.generate_from_dict([
    {"sepal_length": 5.1, "species": "setosa"},
    {"sepal_length": 6.4, "species": "versicolor"},
])

print(card.to_markdown())
print(card.to_json())

# Validate
schema = DatacardSchema()
errors = schema.validate(card.to_dict())
if errors:
    for e in errors:
        print(e)
```

---

## CLI reference

```
usage: datacard-gen [-h] [--name NAME] [--description DESC]
                    [--license LICENSE] [--source SOURCE]
                    [--tags TAGS] [--version VERSION]
                    [--examples N] [--format {markdown,json}]
                    [--output FILE]
                    [input]

positional arguments:
  input               Dataset file (.csv or .json). Reads CSV from stdin if omitted.

options:
  --name NAME         Dataset name (defaults to filename stem).
  --description DESC  Short description of the dataset.
  --license LICENSE   SPDX licence identifier (default: cc-by-4.0).
  --source SOURCE     Source URL or reference string.
  --tags TAGS         Comma-separated tags.
  --version VERSION   Semantic version string (default: 1.0.0).
  --examples N        Number of example rows to embed (default: 5).
  --format {markdown,json}
                      Output format (default: markdown).
  -o FILE, --output FILE
                      Write output to FILE instead of stdout.
```

---

## Output structure

The generated Markdown card contains:

| Section | Content |
|---------|---------|
| YAML front-matter | `pretty_name`, `license`, `version`, `tags` |
| Dataset Description | User-supplied description |
| Dataset Structure | Row/column counts, source URL |
| Data Fields | Per-column type, missing rate, statistics or top values |
| Example Rows | First *N* rows as a Markdown table |
| Dataset Statistics | Summary table of all columns |
| License | Licence statement |

---

## Development

```bash
git clone https://github.com/vdeshmukh203/datacard-gen.git
cd datacard-gen
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Citation

If you use `datacard-gen` in research, please cite:

```bibtex
@article{deshmukh2026datacardgen,
  title   = {datacard-gen: Automated generation of dataset documentation cards for machine learning research},
  author  = {Deshmukh, Vaibhav},
  journal = {Journal of Open Source Software},
  year    = {2026},
}
```

---

## License

MIT © Vaibhav Deshmukh
