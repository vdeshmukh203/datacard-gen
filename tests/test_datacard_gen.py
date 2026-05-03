"""
Tests for datacard_gen — covering helpers, data model, generator API, and CLI.
"""

import csv
import io
import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so `import datacard_gen` works
# whether tests are run from the repo root or from the tests/ directory.
sys.path.insert(0, str(Path(__file__).parent.parent))

import datacard_gen as dcg
from datacard_gen import (
    DataCard,
    DatacardGenerator,
    FieldInfo,
    _field_stats,
    _is_numeric,
    _safe_float,
)


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_valid_float(self):
        assert _safe_float("1.5") == 1.5

    def test_valid_int(self):
        assert _safe_float("42") == 42.0

    def test_negative(self):
        assert _safe_float("-3.14") == pytest.approx(-3.14)

    def test_invalid_string(self):
        assert _safe_float("bad") is None

    def test_none_input(self):
        assert _safe_float(None) is None

    def test_empty_string(self):
        assert _safe_float("") is None


# ---------------------------------------------------------------------------
# _is_numeric
# ---------------------------------------------------------------------------

class TestIsNumeric:
    def test_all_numeric(self):
        assert _is_numeric(["1", "2", "3.0", "4"])

    def test_single_float(self):
        assert _is_numeric(["3.14"])

    def test_all_strings(self):
        assert not _is_numeric(["hello", "world"])

    def test_empty_list(self):
        assert not _is_numeric([])

    def test_all_whitespace(self):
        assert not _is_numeric(["  ", "\t"])

    def test_mixed_below_threshold(self):
        # 2/10 numeric = 20 % < 80 %
        assert not _is_numeric(["1", "2"] + ["text"] * 8)

    def test_mixed_above_threshold(self):
        # 9/10 numeric = 90 % ≥ 80 %
        assert _is_numeric(["1", "2", "3", "4", "5", "6", "7", "8", "9", "text"])


# ---------------------------------------------------------------------------
# _field_stats
# ---------------------------------------------------------------------------

class TestFieldStats:
    def test_numeric_stats(self):
        stats = _field_stats(["1", "2", "3", "4", "5"])
        assert stats["type"] == "numeric"
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["median"] == 3.0
        assert stats["missing"] == 0
        assert stats["missing_pct"] == 0.0
        assert stats["unique"] == 5

    def test_numeric_std(self):
        # std of [2, 4, 4, 4, 5, 5, 7, 9] (population) = 2.0
        stats = _field_stats(["2", "4", "4", "4", "5", "5", "7", "9"])
        assert stats["std"] == pytest.approx(2.0)

    def test_numeric_missing(self):
        stats = _field_stats(["1", "2", "", "4"])
        assert stats["missing"] == 1
        assert stats["missing_pct"] == pytest.approx(25.0)

    def test_categorical_stats(self):
        stats = _field_stats(["cat", "dog", "cat", "bird", "cat"])
        assert stats["type"] == "categorical"
        top = {v["value"]: v["count"] for v in stats["top_values"]}
        assert top["cat"] == 3
        assert top["dog"] == 1

    def test_categorical_top5_limit(self):
        values = [str(i) for i in range(10)]  # all unique → categorical
        # Make 10 distinct categories to ensure top_values is capped at 5
        cats = ["a", "a", "b", "b", "c", "c", "d", "d", "e", "e", "f", "f"]
        stats = _field_stats(cats)
        assert len(stats["top_values"]) <= 5

    def test_all_missing(self):
        stats = _field_stats(["", "  ", ""])
        assert stats["missing"] == 3
        assert stats["missing_pct"] == 100.0
        assert stats["unique"] == 0

    def test_single_value(self):
        stats = _field_stats(["42"])
        assert stats["type"] == "numeric"
        assert stats["median"] == 42.0


# ---------------------------------------------------------------------------
# FieldInfo
# ---------------------------------------------------------------------------

class TestFieldInfo:
    def test_to_dict(self):
        fi = FieldInfo(name="age", dtype="numeric", stats={"min": 0, "max": 100})
        d = fi.to_dict()
        assert d["name"] == "age"
        assert d["dtype"] == "numeric"
        assert d["stats"]["max"] == 100


# ---------------------------------------------------------------------------
# DataCard
# ---------------------------------------------------------------------------

SAMPLE_FIELDS = [
    FieldInfo("age", "numeric", {"min": 18, "max": 65, "mean": 35.0, "std": 10.0,
                                  "median": 34.0, "missing": 0, "missing_pct": 0.0, "unique": 40}),
    FieldInfo("city", "categorical", {"top_values": [{"value": "NYC", "count": 5}],
                                       "missing": 1, "missing_pct": 10.0, "unique": 3}),
]


class TestDataCard:
    def _make_card(self):
        return DataCard(
            name="Test Dataset",
            description="A test.",
            num_rows=10,
            num_cols=2,
            fields=SAMPLE_FIELDS,
            license="cc-by-4.0",
            source="https://example.com",
            tags=["nlp", "test"],
            version="1.2.3",
        )

    def test_to_dict_keys(self):
        d = self._make_card().to_dict()
        for key in ("name", "description", "num_rows", "num_cols", "license",
                    "source", "version", "tags", "fields"):
            assert key in d

    def test_to_dict_fields(self):
        d = self._make_card().to_dict()
        assert len(d["fields"]) == 2
        assert d["fields"][0]["name"] == "age"

    def test_to_json_valid(self):
        j = self._make_card().to_json()
        parsed = json.loads(j)
        assert parsed["num_rows"] == 10

    def test_to_markdown_contains_name(self):
        md = self._make_card().to_markdown()
        assert "Test Dataset" in md

    def test_to_markdown_yaml_frontmatter(self):
        md = self._make_card().to_markdown()
        assert md.startswith("---")
        assert "license: cc-by-4.0" in md
        assert "version: 1.2.3" in md
        assert "  - nlp" in md

    def test_to_markdown_field_sections(self):
        md = self._make_card().to_markdown()
        assert "### `age` (numeric)" in md
        assert "### `city` (categorical)" in md

    def test_to_markdown_statistics_table(self):
        md = self._make_card().to_markdown()
        # Table separator must not contain a stray `]`
        assert "|-------|------|---------|--------|" in md
        assert "|-------|------|---------|--------|]" not in md

    def test_to_markdown_datasheets_sections(self):
        md = self._make_card().to_markdown()
        for section in ("## Motivation", "## Composition", "## Collection Process",
                        "## Uses", "## Distribution", "## Maintenance"):
            assert section in md

    def test_to_markdown_license_section(self):
        md = self._make_card().to_markdown()
        assert "cc-by-4.0" in md

    def test_to_markdown_source(self):
        md = self._make_card().to_markdown()
        assert "https://example.com" in md

    def test_to_markdown_no_tags(self):
        card = DataCard("X", "desc", 1, 1)
        md = card.to_markdown()
        assert "tags:" not in md

    def test_empty_fields(self):
        card = DataCard("Empty", "none", 0, 0)
        md = card.to_markdown()
        assert "Empty" in md


# ---------------------------------------------------------------------------
# DatacardGenerator
# ---------------------------------------------------------------------------

class TestDatacardGenerator:
    def test_generate_from_dict_basic(self):
        gen = DatacardGenerator(name="Demo")
        card = gen.generate_from_dict([
            {"x": 1, "y": "a"},
            {"x": 2, "y": "b"},
        ])
        assert card.name == "Demo"
        assert card.num_rows == 2
        assert card.num_cols == 2

    def test_generate_from_dict_numeric_column(self):
        gen = DatacardGenerator()
        card = gen.generate_from_dict([{"val": i} for i in range(10)])
        assert card.fields[0].dtype == "numeric"

    def test_generate_from_dict_categorical_column(self):
        gen = DatacardGenerator()
        card = gen.generate_from_dict([{"label": c} for c in "abcde"])
        assert card.fields[0].dtype == "categorical"

    def test_generate_from_dict_empty(self):
        gen = DatacardGenerator()
        card = gen.generate_from_dict([])
        assert card.num_rows == 0
        assert card.num_cols == 0

    def test_generate_list_input(self):
        gen = DatacardGenerator()
        data = [{"a": 1}, {"a": 2}]
        card = gen.generate(data)
        assert card.num_rows == 2

    def test_generate_column_dict_input(self):
        gen = DatacardGenerator()
        card = gen.generate({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_unsupported_type(self):
        gen = DatacardGenerator()
        with pytest.raises(TypeError):
            gen.generate(42)

    def test_generate_from_csv(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("name,score\nAlice,95\nBob,87\nCarol,92\n", encoding="utf-8")
        gen = DatacardGenerator(name="Scores")
        card = gen.generate_from_csv(csv_file)
        assert card.num_rows == 3
        assert card.num_cols == 2
        score_field = next(f for f in card.fields if f.name == "score")
        assert score_field.dtype == "numeric"
        assert score_field.stats["mean"] == pytest.approx(91.333, rel=1e-3)

    def test_generate_path_input(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x,y\n1,a\n2,b\n", encoding="utf-8")
        gen = DatacardGenerator()
        card = gen.generate(csv_file)
        assert card.num_rows == 2

    def test_metadata_propagation(self):
        gen = DatacardGenerator(
            name="N", description="D", license="mit",
            source="http://x.com", tags=["t1"], version="2.0.0",
        )
        card = gen.generate_from_dict([{"v": 1}])
        assert card.license == "mit"
        assert card.source == "http://x.com"
        assert "t1" in card.tags
        assert card.version == "2.0.0"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_main_csv_markdown(self, tmp_path, capsys):
        csv_file = tmp_path / "d.csv"
        csv_file.write_text("a,b\n1,x\n2,y\n")
        rc = dcg.main([str(csv_file)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "---" in out
        assert "## Dataset Summary" in out

    def test_main_csv_json(self, tmp_path, capsys):
        csv_file = tmp_path / "d.csv"
        csv_file.write_text("a,b\n1,x\n")
        rc = dcg.main([str(csv_file), "--format", "json"])
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["num_rows"] == 1

    def test_main_output_file(self, tmp_path):
        csv_file = tmp_path / "d.csv"
        out_file = tmp_path / "card.md"
        csv_file.write_text("x\n1\n2\n")
        rc = dcg.main([str(csv_file), "-o", str(out_file)])
        assert rc == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "---" in content

    def test_main_missing_file(self, capsys):
        rc = dcg.main(["nonexistent.csv"])
        assert rc == 1
        assert "Error" in capsys.readouterr().err

    def test_main_with_name_flag(self, tmp_path, capsys):
        csv_file = tmp_path / "d.csv"
        csv_file.write_text("v\n1\n")
        dcg.main([str(csv_file), "--name", "Custom Name"])
        out = capsys.readouterr().out
        assert "Custom Name" in out

    def test_cli_alias(self):
        assert dcg._cli is dcg.main
