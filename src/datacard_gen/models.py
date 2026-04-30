from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FieldInfo:
    name: str
    dtype: str
    stats: Dict[str, Any]

    def to_dict(self) -> dict:
        return {"name": self.name, "dtype": self.dtype, "stats": self.stats}


@dataclass
class DataCard:
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
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
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
            "---", "",
            f"# {self.name}", "",
            "## Dataset Description", "",
            self.description, "",
            "## Dataset Structure", "",
            f"- **Rows:** {self.num_rows:,}",
            f"- **Columns:** {self.num_cols}",
        ]
        if self.source:
            lines.append(f"- **Source:** {self.source}")
        lines += ["", "## Data Fields", ""]
        for fi in self.fields:
            s = fi.stats
            lines += [
                f"### `{fi.name}` ({fi.dtype})", "",
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
            "## Dataset Statistics", "",
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
            "## License", "",
            f"This dataset is released under the **{self.license}** license.",
        ]
        return "\n".join(lines)
