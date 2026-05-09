"""Data models and validation schema for dataset datacards."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


# ── Data models ───────────────────────────────────────────────────────────── #

@dataclass
class FieldInfo:
    """Metadata and statistics for a single dataset field (column)."""

    name: str
    dtype: str
    stats: Dict[str, Any]

    def to_dict(self) -> dict:
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


@dataclass
class DataCard:
    """Structured representation of a Hugging Face-compatible dataset card."""

    name: str
    description: str
    num_rows: int
    num_cols: int
    fields: List[FieldInfo] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    license: str = "unknown"
    source: str = ""
    version: str = "1.0.0"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "license": self.license,
            "source": self.source,
            "version": self.version,
            "tags": self.tags,
            "fields": [f.to_dict() for f in self.fields],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialise the card to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render the card as a Hugging Face-compatible Markdown datacard."""
        lines = [
            "---",
            f"pretty_name: {self.name}",
            f"license: {self.license}",
            f"version: {self.version}",
        ]
        if self.tags:
            lines.append("tags:")
            for t in self.tags:
                lines.append(f"  - {t}")
        lines += [
            "---",
            "",
            f"# {self.name}",
            "",
            "## Dataset Description",
            "",
            self.description,
            "",
            "## Dataset Structure",
            "",
            f"- **Rows:** {self.num_rows:,}",
            f"- **Columns:** {self.num_cols}",
        ]
        if self.source:
            lines.append(f"- **Source:** {self.source}")
        lines += ["", "## Data Fields", ""]
        for fi in self.fields:
            s = fi.stats
            lines += [
                f"### `{fi.name}` ({fi.dtype})",
                "",
                f"- **Missing:** {s.get('missing', 0)} ({s.get('missing_pct', 0):.1f}%)",
                f"- **Unique values:** {s.get('unique', '?')}",
            ]
            if fi.dtype == "numeric":
                lines += [
                    f"- **Min:** {s.get('min')}",
                    f"- **Max:** {s.get('max')}",
                    f"- **Mean:** {s.get('mean')}",
                    f"- **Std:** {s.get('std')}",
                    f"- **Median:** {s.get('median')}",
                ]
            else:
                top = s.get("top_values", [])
                if top:
                    tv = ", ".join("{} ({})".format(v["value"], v["count"]) for v in top)
                    lines.append(f"- **Top values:** {tv}")
            lines.append("")
        lines += [
            "## Dataset Statistics",
            "",
            "| Field | Type | Missing | Unique |",
            "|-------|------|---------|--------|",
        ]
        for fi in self.fields:
            s = fi.stats
            lines.append(
                f"| {fi.name} | {fi.dtype} | {s.get('missing_pct', 0):.1f}% | {s.get('unique', '?')} |"
            )
        lines += [
            "",
            "## License",
            "",
            f"This dataset is released under the **{self.license}** license.",
        ]
        return "\n".join(lines)


# ── Validation schema ─────────────────────────────────────────────────────── #

_REQUIRED_KEYS = frozenset({"name", "description", "num_rows", "num_cols", "license", "version"})


@dataclass
class ValidationError:
    """Represents a single validation failure."""

    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.field}: {self.message}"


class DatacardSchema:
    """Validates datacard dicts against the Hugging Face DatasetCard schema.

    Example::

        schema = DatacardSchema()
        errors = schema.validate(card.to_dict())
        if errors:
            for e in errors:
                print(e)
    """

    def validate(self, card_dict: Dict[str, Any]) -> List[ValidationError]:
        """Return a list of :class:`ValidationError`; an empty list means valid."""
        errors: List[ValidationError] = []
        for key in sorted(_REQUIRED_KEYS):
            if key not in card_dict:
                errors.append(
                    ValidationError(field=key, message=f"Required field '{key}' is missing")
                )
        if "num_rows" in card_dict and not isinstance(card_dict["num_rows"], int):
            errors.append(
                ValidationError(field="num_rows", message="'num_rows' must be an integer")
            )
        if "num_cols" in card_dict and not isinstance(card_dict["num_cols"], int):
            errors.append(
                ValidationError(field="num_cols", message="'num_cols' must be an integer")
            )
        for i, fld in enumerate(card_dict.get("fields", [])):
            if "name" not in fld:
                errors.append(
                    ValidationError(
                        field=f"fields[{i}].name", message="Each field must have a 'name'"
                    )
                )
            if "dtype" not in fld:
                errors.append(
                    ValidationError(
                        field=f"fields[{i}].dtype", message="Each field must have a 'dtype'"
                    )
                )
        return errors

    def is_valid(self, card_dict: Dict[str, Any]) -> bool:
        """Return ``True`` if *card_dict* passes all validation checks."""
        return not self.validate(card_dict)
