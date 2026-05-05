# datacard-gen

[![CI](https://github.com/vdeshmukh203/datacard-gen/actions/workflows/ci.yml/badge.svg)](https://github.com/vdeshmukh203/datacard-gen/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python ≥ 3.8](https://img.shields.io/badge/python-%E2%89%A53.8-blue.svg)](https://www.python.org/)

Automated dataset documentation card generator for machine learning research.

`datacard-gen` profiles CSV and JSON dataset files and generates structured,
[Hugging Face-compatible](https://huggingface.co/docs/hub/datasets-cards) dataset
cards in Markdown or JSON format — no external dependencies required (pure Python
standard library).

---

## Installation

```bash
pip install datacard-gen
```

Or install directly from source:

```bash
git clone https://github.com/vdeshmukh203/datacard-gen
cd datacard-gen
pip install .
```

For the optional tkinter GUI on Linux, also install:

```bash
sudo apt install python3-tk          # Debian/Ubuntu
sudo dnf install python3-tkinter     # Fedora/RHEL
```

---

## Quick Start

### Command-line interface

```bash
# Generate a Markdown card from a CSV file (output to stdout)
datacard-gen dataset.csv

# Customise metadata and write to a file
datacard-gen dataset.csv \
  --name "My Dataset" \
  --description "A curated sample dataset." \
  --license cc-by-4.0 \
  --tags "nlp,classification" \
  --output README.md

# Output JSON
datacard-gen dataset.csv --format json

# Pipe CSV from stdin
cat dataset.csv | datacard-gen --name "Streamed Dataset"

# JSON input file
datacard-gen records.json --name "Event Log"
```

### Python API

```python
from datacard_gen import DatacardGenerator

gen = DatacardGenerator(
    name="My Dataset",
    description="A sample dataset for binary classification.",
    license="cc-by-4.0",
    tags=["tabular", "classification"],
)

# From a CSV file
card = gen.generate("dataset.csv")

# From a JSON file (row- or column-oriented)
card = gen.generate("dataset.json")

# From a list of row dicts
card = gen.generate([{"name": "Alice", "score": 90}, {"name": "Bob", "score": 85}])

# From a column-oriented dict
card = gen.generate({"name": ["Alice", "Bob"], "score": [90, 85]})

# Render
print(card.to_markdown())   # Hugging Face-compatible Markdown
print(card.to_json())       # Structured JSON
```

### Graphical interface

```bash
datacard-gen-gui
```

The GUI provides file selection, metadata editing, format selection, a live
preview of the generated card, and one-click save.

---

## Features

| Feature | Detail |
|---------|--------|
| Automatic type detection | Numeric vs. categorical columns (≥ 80 % parseable-as-float threshold) |
| Descriptive statistics | min, max, mean, population std dev, median for numeric; top-5 value frequencies for categorical |
| Missing-value reporting | Count and percentage per column |
| HF Hub-compatible output | YAML frontmatter (`pretty_name`, `license`, `version`, `tags`) |
| Multiple output formats | Markdown (default) and JSON |
| Multiple input formats | CSV (stdin or file) and JSON (row- or column-oriented) |
| No external dependencies | Pure Python standard library (≥ 3.8) |
| GUI | Tkinter desktop application (`datacard-gen-gui`) |

---

## CLI reference

```
usage: datacard-gen [-h] [--name NAME] [--description DESC]
                    [--license LICENSE] [--source SOURCE]
                    [--tags TAGS] [--version VERSION]
                    [--format {markdown,json}] [--output FILE]
                    [FILE]

positional arguments:
  FILE                  Input CSV or JSON file (reads from stdin if omitted).

options:
  --name NAME           Dataset name.
  --description DESC    Short dataset description.
  --license LICENSE     SPDX licence identifier. (default: cc-by-4.0)
  --source SOURCE       Dataset source URL or citation.
  --tags TAGS           Comma-separated list of tags.
  --version VERSION     Dataset version string. (default: 1.0.0)
  --format {markdown,json}
                        Output format. (default: markdown)
  --output FILE, -o FILE
                        Write output to FILE instead of stdout.
```

---

## Supported input formats

| Format | Notes |
|--------|-------|
| CSV | UTF-8-encoded; read via `csv.DictReader` |
| JSON — row-oriented | Array of objects: `[{"col": val, …}, …]` |
| JSON — column-oriented | Object of arrays: `{"col": [v1, v2, …], …}` |

---

## Example output (Markdown)

```markdown
---
pretty_name: iris
license: cc-by-4.0
version: 1.0.0
tags:
  - tabular
---

# iris

## Dataset Description

A dataset generated automatically.

## Dataset Structure

- **Rows:** 150
- **Columns:** 5

## Data Fields

### `sepal_length` (numeric)

- **Missing:** 0 (0.0%)
- **Unique values:** 35
- **Min:** 4.3
- **Max:** 7.9
- **Mean:** 5.8433
- **Std:** 0.8253
- **Median:** 5.8

...

## Dataset Statistics

| Field | Type | Missing | Unique |
|-------|------|---------|--------|
| sepal_length | numeric | 0.0% | 35 |
...

## License

This dataset is released under the **cc-by-4.0** license.
```

---

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/
```

---

## Citation

If you use `datacard-gen` in your research, please cite:

```bibtex
@software{deshmukh2026datacardgen,
  author  = {Vaibhav Deshmukh},
  title   = {datacard-gen: Automated generation of dataset documentation cards
             for machine learning research},
  year    = {2026},
  url     = {https://github.com/vdeshmukh203/datacard-gen},
  version = {0.1.0},
}
```

---

## License

MIT © 2026 Vaibhav Deshmukh — see [LICENSE](LICENSE).
