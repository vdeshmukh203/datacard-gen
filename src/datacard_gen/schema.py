from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .models import DataCard

_SPDX_COMMON = {
    "mit", "apache-2.0", "gpl-2.0", "gpl-3.0", "lgpl-2.1", "lgpl-3.0",
    "bsd-2-clause", "bsd-3-clause", "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0",
    "cc-by-nc-4.0", "cc-by-nc-sa-4.0", "cc-by-nd-4.0", "openrail", "unknown",
}
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_VALID_DTYPES = {"numeric", "categorical"}
_PLACEHOLDER_DESCRIPTIONS = {
    "", "a dataset.", "a dataset generated automatically.",
}


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"Valid: {self.valid}"]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


class DatacardSchema:
    """Validates a :class:`~datacard_gen.models.DataCard` against the Hugging Face dataset card schema."""

    def validate(self, card: DataCard) -> ValidationResult:
        """Return a :class:`ValidationResult` with any errors and warnings found."""
        errors: List[str] = []
        warnings: List[str] = []

        if not card.name or not card.name.strip():
            errors.append("'name' is required and must not be empty.")

        if card.description.strip().lower() in _PLACEHOLDER_DESCRIPTIONS:
            warnings.append(
                "'description' appears to be a placeholder; provide a meaningful description."
            )

        if not _SEMVER_RE.match(card.version):
            warnings.append(
                f"'version' '{card.version}' does not follow semantic versioning (MAJOR.MINOR.PATCH)."
            )

        if card.license.lower() not in _SPDX_COMMON:
            warnings.append(
                f"'license' '{card.license}' is not a recognised SPDX identifier. "
                "See https://spdx.org/licenses/"
            )

        if not card.tags:
            warnings.append("'tags' is empty. Adding relevant tags improves Hub discoverability.")

        if not card.source:
            warnings.append("'source' is empty. Documenting data provenance is strongly recommended.")

        if card.num_rows == 0:
            warnings.append("Dataset has zero rows — the input file may be empty.")

        for fi in card.fields:
            if not fi.name or not fi.name.strip():
                errors.append("A field has an empty name.")
            if fi.dtype not in _VALID_DTYPES:
                errors.append(
                    f"Field '{fi.name}' has unknown dtype '{fi.dtype}'. "
                    f"Expected one of: {sorted(_VALID_DTYPES)}."
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)
