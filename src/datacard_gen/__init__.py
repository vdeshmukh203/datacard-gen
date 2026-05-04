"""
datacard_gen: Automated dataset documentation card generator.

Re-exports the public API from the top-level ``datacard_gen`` module so that
both ``import datacard_gen`` (root module) and ``from datacard_gen import …``
resolve correctly regardless of how the package is installed.
"""

import importlib
import sys

# Ensure the repo root is importable when the package is used from src/
import pathlib as _pathlib

_root = str(_pathlib.Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

_mod = importlib.import_module("datacard_gen")

__version__: str = _mod.__version__
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

DatacardGenerator = _mod.DatacardGenerator
DataCard = _mod.DataCard
FieldInfo = _mod.FieldInfo

__all__ = ["DatacardGenerator", "DataCard", "FieldInfo"]
