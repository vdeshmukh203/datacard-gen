"""
datacard_gen — Automated dataset documentation card generator.

Analyses a CSV or JSON dataset file and generates a structured dataset card
conforming to the Hugging Face DatasetCard schema.  Infers statistics, feature
types, and missing-value rates from the data itself, reducing the manual effort
required for reproducible dataset documentation.

When installed (``pip install datacard-gen``), import the public API as::

    from datacard_gen import DatacardGenerator, DataCard, FieldInfo
"""

__version__ = "0.1.0"
__author__ = "Vaibhav Deshmukh"
__license__ = "MIT"

# The package is distributed as a single-file module (datacard_gen.py).
# This __init__.py provides package-level metadata; the classes are imported
# directly from the installed module at runtime.
__all__ = ["DatacardGenerator", "DataCard", "FieldInfo"]
