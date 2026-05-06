"""
Re-export DatacardGenerator from the top-level module for package-level access.
"""

from datacard_gen import DatacardGenerator, DataCard, FieldInfo

__all__ = ["DatacardGenerator", "DataCard", "FieldInfo"]
