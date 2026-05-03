# datacard-gen

Automated dataset documentation card generator for machine learning research.

`datacard-gen` profiles a CSV dataset, computes descriptive statistics, detects
column types, and emits a Markdown documentation card following the
[*Datasheets for Datasets*](https://arxiv.org/abs/1803.09010) framework
(Gebru et al., 2021) and compatible with the
[Hugging Face Hub](https://huggingface.co/docs/hub/datasets-cards) schema.

---

## Features

- **Zero dependencies** — pure Python standard library (≥ 3.8).
- **Automatic profiling** — numeric statistics (min, max, mean, std, median)
  and categorical top-value counts per column.
- **Datasheets for Datasets** structure — Motivation, Composition, Collection
  Process, Preprocessing, Uses, Distribution, and Maintenance sections.
- **Hugging Face-compatible** YAML frontmatter (license, version, tags).
- **Multiple input modes** — CSV file, list of dicts, or column-oriented dict.
- **GUI** — Tkinter graphical interface for point-and-click use.

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

## Quick Start

### Command Line

```bash
# Generate a Markdown card (default)
datacard-gen dataset.csv --name "My Dataset" --license cc-by-4.0

# Generate JSON
datacard-gen dataset.csv --format json -o card.json

# Pipe from stdin
cat data.csv | datacard-gen --name "Piped Dataset"

# Launch the GUI
datacard-gen --gui
# or
datacard-gen-gui
```

### Python API

```python
from pathlib import Path
from datacard_gen import DatacardGenerator

gen = DatacardGenerator(
    name="Iris",
    description="Classic flower measurements dataset.",
    license="cc0-1.0",
    tags=["tabular", "biology"],
)

# From a CSV file
card = gen.generate(Path("iris.csv"))

# From a list of dicts
card = gen.generate([{"sepal_len": 5.1, "species": "setosa"}, ...])

# Output
print(card.to_markdown())   # Hugging Face-compatible Markdown
print(card.to_json())       # JSON
```

---

## GUI

Launch the graphical interface:

```bash
datacard-gen-gui
```

Features:
- Browse for a CSV file
- Fill in dataset metadata (name, license, source, tags, version, description)
- Choose Markdown or JSON output
- Live preview pane
- Save As… and Copy to Clipboard buttons

---

## CLI Reference

```
usage: datacard-gen [-h] [--name NAME] [--description DESC]
                    [--license LICENSE] [--source SOURCE]
                    [--tags TAGS] [--version VERSION]
                    [--format {markdown,json}] [--output FILE]
                    [--gui] [csv]

positional arguments:
  csv                   Input CSV file (omit to read from stdin)

options:
  --name NAME           Dataset name
  --description DESC    Short description
  --license LICENSE     SPDX license identifier (default: cc-by-4.0)
  --source SOURCE       Provenance URL or citation
  --tags TAGS           Comma-separated Hugging Face tags
  --version VERSION     Dataset version string (default: 1.0.0)
  --format {markdown,json}  Output format (default: markdown)
  --output FILE, -o FILE    Write to FILE instead of stdout
  --gui                 Launch the graphical user interface
```

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Citation

If you use `datacard-gen` in your research, please cite:

```bibtex
@article{deshmukh2026datacard,
  title   = {datacard-gen: Automated generation of dataset documentation cards
             for machine learning research},
  author  = {Deshmukh, Vaibhav},
  journal = {Journal of Open Source Software},
  year    = {2026},
}
```

---

## License

MIT — see [LICENSE](LICENSE).
