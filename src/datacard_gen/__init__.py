"""
datacard_gen — Automated dataset documentation card generator.

Profiles a dataset (CSV or JSON) and emits a structured dataset card
conforming to the Hugging Face DatasetCard schema and the *Datasheets for
Datasets* framework (Gebru et al., 2021).

Quickstart::

    from datacard_gen import DatacardGenerator
    gen = DatacardGenerator(name="My Dataset", license="cc-by-4.0")
    card = gen.generate_from_csv("data.csv")
    print(card.to_markdown())
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

from .generator import DatacardGenerator
from .models import DataCard, FieldInfo
from .schema import DatacardSchema, ValidationResult

__all__ = [
    "DatacardGenerator",
    "DataCard",
    "FieldInfo",
    "DatacardSchema",
    "ValidationResult",
]
