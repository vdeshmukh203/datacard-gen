"""Schema validation for dataset datacards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


SPDX_LICENSES = {
    "mit", "apache-2.0", "cc-by-4.0", "cc-by-sa-4.0", "cc-by-nc-4.0",
    "cc-by-nc-sa-4.0", "cc-by-nd-4.0", "cc0-1.0", "gpl-2.0", "gpl-3.0",
    "lgpl-2.1", "lgpl-3.0", "bsd-2-clause", "bsd-3-clause", "mpl-2.0",
    "isc", "artistic-2.0", "eupl-1.2", "agpl-3.0", "unknown", "other",
}


@dataclass
class ValidationError:
    field: str
    message: str

    def __str__(self) -> str:
        return f"[{self.field}] {self.message}"


class DatacardSchema:
    """Validate a :class:`~datacard_gen.generator.DataCard` serialisation dict.

    Usage::

        schema = DatacardSchema()
        errors = schema.validate(card.to_dict())
        if errors:
            for e in errors:
                print(e)
    """

    def validate(self, card_dict: Dict[str, Any]) -> List[ValidationError]:
        """Return a (possibly empty) list of :class:`ValidationError` objects."""
        errors: List[ValidationError] = []

        name = card_dict.get("name", "")
        if not isinstance(name, str) or not name.strip():
            errors.append(ValidationError("name", "Dataset name is required and must not be empty."))

        desc = card_dict.get("description", "")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(ValidationError(
                "description", "Description is required and must not be empty."
            ))

        lic = str(card_dict.get("license", "")).lower()
        if lic and lic not in SPDX_LICENSES:
            errors.append(ValidationError(
                "license",
                f"'{lic}' is not a recognised SPDX identifier. "
                f"Common values: {', '.join(sorted(SPDX_LICENSES))}.",
            ))

        num_rows = card_dict.get("num_rows", 0)
        if not isinstance(num_rows, int) or num_rows < 0:
            errors.append(ValidationError("num_rows", "num_rows must be a non-negative integer."))

        version = str(card_dict.get("version", ""))
        if version:
            parts = version.split(".")
            if not (len(parts) == 3 and all(p.isdigit() for p in parts)):
                errors.append(ValidationError(
                    "version",
                    f"'{version}' must follow semantic versioning (e.g. 1.0.0).",
                ))

        tags = card_dict.get("tags", [])
        if not isinstance(tags, list):
            errors.append(ValidationError("tags", "tags must be a list of strings."))
        elif any(not isinstance(t, str) for t in tags):
            errors.append(ValidationError("tags", "Every tag must be a plain string."))

        fields = card_dict.get("fields", [])
        if not isinstance(fields, list):
            errors.append(ValidationError("fields", "fields must be a list."))
        else:
            for i, f in enumerate(fields):
                if not isinstance(f, dict) or "name" not in f or "dtype" not in f:
                    errors.append(ValidationError(
                        f"fields[{i}]", "Each field entry must have 'name' and 'dtype' keys."
                    ))

        return errors

    def is_valid(self, card_dict: Dict[str, Any]) -> bool:
        """Return True if *card_dict* passes all validation checks."""
        return len(self.validate(card_dict)) == 0
