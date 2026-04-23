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

`datacard-gen` is a Python command-line tool that automatically generates structured dataset documentation cards by profiling dataset files and populating a standardised template modelled on the Hugging Face dataset card schema and the broader Data Sheets for Datasets framework [@gebru2021datasheets]. Given a dataset file (CSV, JSON, Parquet, or Arrow) and optional metadata flags, `datacard-gen` computes descriptive statistics, detects column types, estimates missing value rates, samples example rows, and emits a Markdown documentation card that can be committed directly to a repository or uploaded to Hugging Face Hub.

# Statement of Need

Dataset documentation is widely recognised as essential for reproducible machine learning research [@pineau2021improving; @gundersen2018state], yet in practice most datasets are released without any structured documentation because authoring data cards manually is time-consuming. `datacard-gen` lowers the barrier by automating the profiling step: researchers run a single command against their dataset and receive a draft card that covers provenance, structure, statistical summaries, and known limitations. The generated card follows the Hugging Face YAML frontmatter convention, enabling immediate use with Hub APIs. By reducing documentation effort, `datacard-gen` encourages adoption of dataset documentation practices across the research community.

# Acknowledgements

The author used Claude (Anthropic) for drafting portions of this manuscript. All scientific claims and design decisions are the author's own.

# References
