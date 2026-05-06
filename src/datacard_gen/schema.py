"""
Datacard schema definition and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class FieldSchema:
    """Schema descriptor for a single dataset field."""

    name: str
    dtype: str  # "numeric" or "categorical"
    description: str = ""

    def validate(self) -> List[str]:
        issues = []
        if not self.name.strip():
            issues.append("field name must not be empty")
        if self.dtype not in ("numeric", "categorical"):
            issues.append(f"field '{self.name}': dtype must be 'numeric' or 'categorical', got '{self.dtype}'")
        return issues


@dataclass
class DatacardSchema:
    """
    Metadata schema for a dataset datacard.

    Used to validate datacard inputs before generating documentation.
    Follows the Hugging Face dataset card YAML frontmatter convention.
    """

    name: str
    description: str
    license: str = "cc-by-4.0"
    source: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    fields: List[FieldSchema] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Return a list of validation issues; empty list means the schema is valid."""
        issues: List[str] = []
        if not self.name.strip():
            issues.append("name is required")
        if not self.description.strip():
            issues.append("description is required")
        if self.license in ("", "unknown"):
            issues.append("license should be a valid SPDX identifier (e.g. 'cc-by-4.0', 'mit')")
        for fs in self.fields:
            issues.extend(fs.validate())
        return issues

    def is_valid(self) -> bool:
        return len(self.validate()) == 0
