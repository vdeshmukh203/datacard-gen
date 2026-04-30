# datacard-gen

Automated dataset documentation card generator for machine learning research.

`datacard-gen` profiles a CSV or JSON dataset and emits a structured
[Hugging Face dataset card](https://huggingface.co/docs/hub/datasets-cards)
(Markdown + YAML frontmatter) following the
[Datasheets for Datasets](https://dl.acm.org/doi/10.1145/3458723) framework
(Gebru et al., 2021).

---

## Features

- Detects numeric vs. categorical columns automatically
- Computes per-column statistics (min, max, mean, std, median, top values, missing-value rate)
- Validates the generated card against the Hugging Face schema (`--validate`)
- Outputs Markdown (default) or JSON
- Graphical user interface (`datacard-gen-gui`) built on stdlib `tkinter`
- Zero runtime dependencies — stdlib only

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

Requires Python ≥ 3.8.

---

## Quick start

### Command line

```bash
# Basic usage
datacard-gen dataset.csv -o README.md

# JSON dataset, add metadata, validate
datacard-gen dataset.json \
    --name "My Dataset" \
    --description "Tabular survey results from 2025." \
    --license cc-by-4.0 \
    --source "https://example.org/data" \
    --tags nlp,survey \
    --validate \
    -o README.md

# Read CSV from stdin, emit JSON
cat data.csv | datacard-gen --name PipedData --format json

# All options
datacard-gen --help
```

### Graphical interface

```bash
datacard-gen-gui
```

The GUI lets you browse for a file, fill in metadata, preview the generated
card, and save it — all without touching the command line.

### Python API

```python
from datacard_gen import DatacardGenerator, DatacardSchema

gen = DatacardGenerator(
    name="Survey 2025",
    description="Annual survey of ML practitioners.",
    license="cc-by-4.0",
    source="https://example.org/survey",
    tags=["survey", "nlp"],
)

card = gen.generate_from_csv("data.csv")   # or generate_from_json / generate_from_dict

# Validate before publishing
result = DatacardSchema().validate(card)
if not result.valid:
    print(result)

print(card.to_markdown())
print(card.to_json())
```

---

## Output format

The generated Markdown card includes a YAML frontmatter block compatible with
the Hugging Face Hub API, followed by human-readable sections:

```
---
pretty_name: Survey 2025
license: cc-by-4.0
version: 1.0.0
tags:
  - survey
  - nlp
---

# Survey 2025

## Dataset Description
...

## Dataset Structure
- Rows: 10,000
- Columns: 8

## Data Fields
### `age` (numeric)
- Missing: 12 (0.1%)
- Min: 18 / Max: 90 / Mean: 34.2 / Std: 11.5 / Median: 32.0

### `occupation` (categorical)
- Top values: Engineer (2341), Researcher (1890), ...

## Dataset Statistics
| Field      | Type        | Missing | Unique |
|------------|-------------|---------|--------|
| age        | numeric     | 0.1%    | 73     |
| occupation | categorical | 0.0%    | 42     |
```

---

## Supported input formats

| Format | Extension | Method                   |
|--------|-----------|--------------------------|
| CSV    | `.csv`    | `generate_from_csv()`    |
| JSON   | `.json`   | `generate_from_json()`   |
| dict   | (in-memory) | `generate_from_dict()` |

JSON files may be either a **list of records** (`[{…}, {…}]`) or a
**column-oriented dict** (`{"col": […], …}`).

---

## Validation

`DatacardSchema.validate()` returns a `ValidationResult` with:

- **errors** — missing required fields or invalid dtypes (block publishing)
- **warnings** — placeholder descriptions, unknown SPDX licenses, empty tags, etc.

```python
from datacard_gen import DatacardSchema
result = DatacardSchema().validate(card)
print(result)  # Valid: True / ERROR: … / WARNING: …
```

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

---

## Citation

If you use `datacard-gen` in your research, please cite:

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

MIT © Vaibhav Deshmukh
