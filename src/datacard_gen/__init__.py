"""
datacard_gen: Automated dataset documentation card generator.

Analyses CSV files and generates structured dataset documentation cards
conforming to the Hugging Face DatasetCard schema and the Datasheets for
Datasets framework (Gebru et al., 2021).

Quick start::

    from datacard_gen import DatacardGenerator

    gen = DatacardGenerator(name="My Dataset", license="cc-by-4.0")
    card = gen.generate_from_csv("dataset.csv")
    print(card.to_markdown())
"""

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

from .generator import DataCard, DatacardGenerator, FieldInfo
from .schema import DatacardSchema, ValidationError

__all__ = [
    "DatacardGenerator",
    "DataCard",
    "FieldInfo",
    "DatacardSchema",
    "ValidationError",
]
