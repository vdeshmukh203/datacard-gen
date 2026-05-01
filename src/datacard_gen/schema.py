"""Schema validation for datacards."""
from __future__ import annotations

from typing import Any, Dict, List

VALID_SPDX_LICENSES = {
    "mit", "apache-2.0", "gpl-2.0", "gpl-3.0", "lgpl-2.1", "lgpl-3.0",
    "bsd-2-clause", "bsd-3-clause", "cc-by-4.0", "cc-by-sa-4.0",
    "cc-by-nc-4.0", "cc-by-nc-sa-4.0", "cc0-1.0", "unlicense",
    "agpl-3.0", "mpl-2.0", "isc", "eupl-1.2", "other", "unknown",
}

REQUIRED_FIELDS = {"name", "description", "num_rows", "num_cols", "fields"}


class ValidationError(ValueError):
    """Raised by :meth:`DatacardSchema.validate_strict` when a card is invalid."""


class DatacardSchema:
    """Validates and normalises DataCard dictionaries against the schema.

    Two modes are available:

    * :meth:`validate` — returns a list of warning strings (empty = valid).
    * :meth:`validate_strict` — raises :class:`ValidationError` on the first
      set of issues.
    """

    @staticmethod
    def validate(card_dict: Dict[str, Any]) -> List[str]:
        """Return a list of validation warnings; an empty list means the card is valid."""
        warnings: List[str] = []

        missing = REQUIRED_FIELDS - set(card_dict.keys())
        for f in sorted(missing):
            warnings.append(f"Missing required field: '{f}'")

        lic = card_dict.get("license", "")
        if lic and lic.lower() not in VALID_SPDX_LICENSES:
            warnings.append(
                f"License '{lic}' is not a recognised SPDX identifier. "
                "Use 'other' or 'unknown' if needed."
            )

        if card_dict.get("num_rows", 0) < 0:
            warnings.append("'num_rows' must be non-negative.")

        if card_dict.get("num_cols", 0) < 0:
            warnings.append("'num_cols' must be non-negative.")

        for i, fld in enumerate(card_dict.get("fields", [])):
            if "name" not in fld:
                warnings.append(f"Field at index {i} is missing 'name'.")
            if "dtype" not in fld:
                warnings.append(f"Field at index {i} is missing 'dtype'.")

        return warnings

    @staticmethod
    def validate_strict(card_dict: Dict[str, Any]) -> None:
        """Raise :class:`ValidationError` if *card_dict* has any schema violations."""
        issues = DatacardSchema.validate(card_dict)
        if issues:
            raise ValidationError(
                "Datacard validation failed:\n"
                + "\n".join(f"  - {w}" for w in issues)
            )
