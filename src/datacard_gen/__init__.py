"""
datacard_gen: Automated dataset documentation card generator.

Analyses a dataset file (CSV or JSON) and generates a structured dataset card
conforming to the Hugging Face DatasetCard schema and the Datasheets for
Datasets framework.  Infers statistics, feature types, and missing-value
rates from the data itself, reducing the manual effort required for
reproducible dataset documentation.
"""

from __future__ import annotations

# Re-export the public API from the top-level module so that both
#   ``import datacard_gen`` (root-level script) and
#   ``from datacard_gen import DatacardGenerator`` (installed package)
#   work identically.
import importlib as _importlib
import sys as _sys

_root = _importlib.import_module("datacard_gen")

DatacardGenerator = _root.DatacardGenerator
DataCard = _root.DataCard
FieldInfo = _root.FieldInfo

__version__ = _root.__version__
__author__ = _root.__author__
__license__ = _root.__license__

__all__ = ["DatacardGenerator", "DataCard", "FieldInfo", "__version__"]
