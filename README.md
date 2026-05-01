# datacard-gen

**Automated dataset documentation card generator** following the
[Datasheets for Datasets](https://dl.acm.org/doi/10.1145/3458723) framework
(Gebru et al., 2021) and the
[Hugging Face DatasetCard](https://huggingface.co/docs/hub/datasets-cards) schema.

[![CI](https://github.com/vdeshmukh203/datacard-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/vdeshmukh203/datacard-gen/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)

---

## Overview

`datacard-gen` profiles a CSV dataset and emits a structured Markdown (or JSON)
documentation card in a single command.  No external dependencies — stdlib only.

**What it does automatically:**

- Detects column types (numeric vs. categorical)
- Computes descriptive statistics (min, max, mean, std, median, top-values)
- Reports missing-value rates per column
- Emits valid Hugging Face YAML frontmatter (tags, license, version)
- Validates the card against the datacard schema

---

## Installation

```bash
pip install datacard-gen          # from PyPI (once published)
# or directly from source:
pip install git+https://github.com/vdeshmukh203/datacard-gen.git
```

Python 3.8 or later, no third-party dependencies required.

---

## Quick start

### Command line

```bash
# Generate a Markdown card (printed to stdout)
datacard-gen dataset.csv

# Write to a file with custom metadata
datacard-gen dataset.csv \
    --name "My Dataset" \
    --description "Collected survey responses 2024." \
    --license cc-by-4.0 \
    --tags survey,text \
    --output README.md

# JSON output + schema validation
datacard-gen dataset.csv --format json --validate -o card.json

# Pipe from stdin
cat dataset.csv | datacard-gen --name "Piped Data"

# Launch the GUI
datacard-gen --gui
# or the dedicated GUI entry point
datacard-gen-gui
```

### Python API

```python
from datacard_gen import DatacardGenerator

gen = DatacardGenerator(
    name="Survey 2024",
    description="Annual survey results.",
    license="cc-by-4.0",
    tags=["survey", "text"],
)

# From a CSV file
card = gen.generate_from_csv("dataset.csv")

# From a list of row dicts
card = gen.generate([{"age": 25, "city": "London"}, {"age": 30, "city": "Paris"}])

# From a column-oriented dict
card = gen.generate({"age": [25, 30], "city": ["London", "Paris"]})

print(card.to_markdown())   # Hugging Face-compatible card
print(card.to_json())       # structured JSON
```

### Schema validation

```python
from datacard_gen import DatacardSchema, ValidationError

warnings = DatacardSchema.validate(card.to_dict())   # returns list of strings
DatacardSchema.validate_strict(card.to_dict())        # raises ValidationError
```

---

## Graphical interface

Run `datacard-gen --gui` (or `datacard-gen-gui`) to open the desktop GUI.

Features:
- Browse for a CSV file
- Fill in dataset metadata (name, description, license, source, tags, version)
- Switch between Markdown and JSON output with live refresh
- One-click schema validation
- Save output to a file

---

## CLI reference

| Option | Default | Description |
|--------|---------|-------------|
| `csv` | stdin | Input CSV file |
| `--name` | file stem | Dataset name |
| `--description` | auto | Short description |
| `--license` | `cc-by-4.0` | SPDX license identifier |
| `--source` | — | Source URL or path |
| `--tags` | — | Comma-separated tags |
| `--version` | `1.0.0` | Dataset version |
| `--format` | `markdown` | `markdown` or `json` |
| `--output / -o` | stdout | Output file |
| `--validate` | off | Validate against schema |
| `--gui` | off | Launch GUI |

---

## Project layout

```
src/datacard_gen/
├── __init__.py       public API
├── generator.py      DatacardGenerator, DataCard, FieldInfo, stats helpers
├── schema.py         DatacardSchema, ValidationError
├── cli.py            command-line entry point
└── gui.py            tkinter GUI
datacard_gen.py       standalone single-file script (no install needed)
tests/
└── test_datacard_gen.py
```

---

## Running tests

```bash
pip install -e . pytest
pytest tests/ -v
```

---

## Contributing

Issues and pull requests are welcome.
Please ensure `pytest tests/` passes before submitting a PR.

---

## Citation

If you use `datacard-gen` in research, please cite:

```bibtex
@article{deshmukh2026datacardgen,
  author  = {Deshmukh, Vaibhav},
  title   = {datacard-gen: Automated generation of dataset documentation cards
             for machine learning research},
  journal = {Journal of Open Source Software},
  year    = {2026}
}
```

---

## License

MIT — see [LICENSE](LICENSE).
