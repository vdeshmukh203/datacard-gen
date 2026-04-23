"""
datacard_gen: Automated dataset documentation card generator.

Analyses a dataset directory or HuggingFace dataset repository and generates
a structured dataset card conforming to the HuggingFace DatasetCard schema.
Infers statistics, feature types, splits, and licence information from the
data itself, reducing the manual effort required for reproducible dataset
documentation.
"""

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

from .generator import DatacardGenerator
from .schema import DatacardSchema

__all__ = ["DatacardGenerator", "DatacardSchema"]
