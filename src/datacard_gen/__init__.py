"""
datacard_gen: Automated dataset documentation card generator.

Analyses a dataset (CSV file, list of dicts, or column-oriented dict) and
generates a structured dataset card conforming to the Hugging Face DatasetCard
schema and the *Datasheets for Datasets* framework (Gebru et al., 2021).

This package re-exports the public API from the root-level ``datacard_gen``
module so that both ``import datacard_gen`` and package-style imports work
consistently.
"""

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

# Re-export the public API from the installed root module.
from datacard_gen import DataCard, DatacardGenerator, FieldInfo  # noqa: F401

__all__ = ["DatacardGenerator", "DataCard", "FieldInfo"]
