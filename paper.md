---
title: 'datacard-gen: Automated generation of dataset documentation cards for machine learning research'
tags:
  - Python
  - datasets
  - documentation
  - machine-learning
  - reproducibility
authors:
  - name: Vaibhav Deshmukh
    orcid: 0000-0001-6745-7062
    affiliation: 1
affiliations:
  - name: Independent Researcher, Nagpur, India
    index: 1
date: 23 April 2026
bibliography: paper.bib
---

# Summary

`datacard-gen` is a Python tool that automatically generates structured dataset
documentation cards by profiling tabular data files and populating a
standardised template modelled on the Hugging Face dataset card schema and the
Datasheets for Datasets framework [@gebru2021datasheets].  Given a CSV file and
optional metadata flags, `datacard-gen` computes descriptive statistics, detects
column types, estimates missing-value rates, and emits a Markdown (or JSON)
documentation card that can be committed directly to a repository or uploaded to
Hugging Face Hub.  The package ships with both a command-line interface and a
cross-platform graphical desktop interface built on Python's standard-library
`tkinter` module, requiring no external dependencies.

# Statement of Need

Dataset documentation is widely recognised as essential for reproducible machine
learning research [@pineau2021improving; @gundersen2018state;
@stodden2016enhancing], yet in practice most datasets are released without any
structured documentation because authoring data cards manually is
time-consuming.  The Datasheets for Datasets proposal [@gebru2021datasheets]
provides a comprehensive questionnaire template, while Hugging Face Hub has
popularised a YAML-frontmatter Markdown format for community-shared datasets
[@huggingface2023datacards]; both still rely on authors manually filling in
fields.

`datacard-gen` lowers this barrier by automating the profiling step.
Researchers run a single command against their dataset and receive a draft card
that covers dataset structure, per-column statistical summaries, missing-value
rates, and provenance metadata.  The generated card follows the Hugging Face
YAML frontmatter convention, enabling immediate use with Hub APIs, and is
simultaneously valid Markdown for plain-text or web rendering.  A built-in
schema validator reports deviations from the expected card structure, helping
authors catch omissions before publication.

## Relation to Existing Tools

Model Cards Toolkit [@mitchell2019model] targets model documentation rather than
dataset documentation.  Pandas Profiling / ydata-profiling generates rich HTML
reports focused on exploratory data analysis, but does not produce
repository-ready Markdown cards and requires several heavyweight dependencies.
`datacard-gen` occupies a complementary niche: a lightweight, dependency-free
tool whose primary output is a publication-ready Markdown file rather than an
interactive report.

# Design and Implementation

`datacard-gen` is implemented in pure Python (≥ 3.8) using only the standard
library.  The core pipeline is:

1. **Ingestion** — CSV files are read with `csv.DictReader`; the API also
   accepts lists of row dicts or column-oriented dicts for programmatic use.
2. **Profiling** — Each column is classified as *numeric* or *categorical* using
   an 80 % majority rule on parseable float values.  Numeric columns receive
   min, max, mean, standard deviation, and median; categorical columns receive
   unique-value count and top-5 frequency table.  Missing values (empty strings)
   are counted and reported as a percentage.
3. **Rendering** — A `DataCard` dataclass serialises to Markdown (with valid
   YAML frontmatter) or JSON via `to_markdown()` / `to_json()`.
4. **Validation** — `DatacardSchema.validate()` checks required fields and
   SPDX licence identifiers, returning a list of human-readable warnings.

The graphical interface (`datacard_gen.gui`) wraps the same pipeline in a
`tkinter` window, making the tool accessible to researchers who prefer not to
use the command line.

# Acknowledgements

The author used Claude (Anthropic) for drafting portions of this manuscript and
for code review assistance.  All scientific claims and design decisions are the
author's own.

# References
