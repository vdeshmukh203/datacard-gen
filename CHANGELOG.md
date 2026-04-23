# Changelog

## [Unreleased]
- Hugging Face Hub dataset loading (#1)
- BLOOM taxonomy integration for task field (#2)
- PDF export of generated datacards (#3)

## [0.1.0] - 2026-04-23
### Added
- Automated datacard generation following Gebru et al. Datasheets for Datasets
- Hugging Face Hub compatible README.md output
- CSV, Parquet, and JSON dataset input support
- Schema validation against datacard specification
- CLI: `datacard-gen generate dataset.csv -o README.md`
- Python API: `DatacardGenerator`, `DatacardSchema`
