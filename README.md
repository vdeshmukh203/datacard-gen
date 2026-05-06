# datacard-gen

**Automated generation of Hugging Face-compatible dataset datacards.**

`datacard-gen` profiles a CSV or JSON dataset file and emits a structured
documentation card (Markdown or JSON) that follows the
[Hugging Face dataset card schema](https://huggingface.co/docs/hub/datasets-cards)
and the [Datasheets for Datasets](https://dl.acm.org/doi/10.1145/3458723) framework.

---

## Features

- Reads **CSV** and **JSON** (list-of-records or columnar-dict) files
- Auto-detects **numeric** vs **categorical** columns
- Computes per-column statistics: count, missing rate, min/max/mean/std/median, top values
- Outputs **Markdown** (Hugging Face YAML frontmatter + human-readable body) or **JSON**
- **CLI**, **Python API**, and **graphical interface (GUI)** included
- **Stdlib-only** — no external runtime dependencies

---

## Installation

```bash
pip install datacard-gen
```

Or from source:

```bash
git clone https://github.com/vdeshmukh203/datacard-gen.git
cd datacard-gen
pip install -e .
```

---

## Quick start

### CLI

```bash
# Generate a Markdown datacard from a CSV file
datacard-gen dataset.csv --name "My Dataset" --license cc-by-4.0

# Write to a file
datacard-gen dataset.csv -o README_dataset.md

# JSON output
datacard-gen dataset.csv --format json

# JSON input
datacard-gen records.json --name "My Records"

# From stdin
cat data.csv | datacard-gen --name "Piped Dataset"
```

### Graphical interface

```bash
datacard-gen-gui
```

A point-and-click window lets you browse to any CSV or JSON file, fill in
metadata, preview the generated datacard, and save or copy the result.

### Python API

```python
from datacard_gen import DatacardGenerator
from pathlib import Path

gen = DatacardGenerator(
    name="Iris",
    description="Classic flower classification dataset.",
    license="cc-by-4.0",
    tags=["tabular", "classification"],
)

# From a file
card = gen.generate(Path("iris.csv"))

# From a list of dicts
card = gen.generate([{"sepal_len": 5.1, "species": "setosa"}, ...])

# Output
print(card.to_markdown())
print(card.to_json())
```

---

## CLI reference

| Flag | Default | Description |
|------|---------|-------------|
| `file` | *(stdin)* | Input CSV or JSON file |
| `--name` | file stem | Dataset name |
| `--description` | auto | Short description |
| `--license` | `cc-by-4.0` | SPDX licence identifier |
| `--source` | | Source URL or citation |
| `--tags` | | Comma-separated tags |
| `--version` | `1.0.0` | Dataset version string |
| `--format` | `markdown` | Output format: `markdown` or `json` |
| `--output` / `-o` | *(stdout)* | Write to file instead of stdout |

---

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

---

## License

MIT © Vaibhav Deshmukh
