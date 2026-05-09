"""
datacard_gen: Automated dataset documentation card generator.

Analyses a CSV dataset and generates a structured dataset card conforming to
the Hugging Face DatasetCard schema, inferring statistics, feature types, and
licence information from the data.

Quick start::

    from datacard_gen import DatacardGenerator
    gen = DatacardGenerator(name="My Dataset", license="cc-by-4.0")
    card = gen.generate_from_csv("data.csv")
    print(card.to_markdown())
"""

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

from .generator import DatacardGenerator
from .schema import DataCard, DatacardSchema, FieldInfo, ValidationError

__all__ = [
    "DatacardGenerator",
    "DatacardSchema",
    "DataCard",
    "FieldInfo",
    "ValidationError",
]
