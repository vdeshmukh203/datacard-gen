"""
datacard_gen — Automated dataset documentation card generator.

Profiles CSV, JSON, Parquet, or Arrow dataset files and emits structured
Markdown or JSON datacards that conform to the Hugging Face DatasetCard
schema and the *Datasheets for Datasets* framework.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

from .generator import DataCard, DatacardGenerator, FieldInfo
from .schema import DatacardSchema

__all__ = [
    "DataCard",
    "DatacardGenerator",
    "DatacardSchema",
    "FieldInfo",
]
