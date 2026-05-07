"""
Tests for the datacard_gen package.

Run with:  pytest tests/ -v
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

from datacard_gen import DataCard, DatacardGenerator, DatacardSchema, FieldInfo
from datacard_gen.generator import (
    _field_stats,
    _is_numeric,
    _percentile,
    _safe_float,
)


# ===========================================================================
# Helper utilities
# ===========================================================================

class TestSafeFloat:
    def test_integer_string(self):
        assert _safe_float("42") == 42.0

    def test_float_string(self):
        assert _safe_float("3.14") == pytest.approx(3.14)

    def test_negative(self):
        assert _safe_float("-7.5") == pytest.approx(-7.5)

    def test_non_numeric(self):
        assert _safe_float("hello") is None

    def test_none_input(self):
        assert _safe_float(None) is None

    def test_empty_string(self):
        assert _safe_float("") is None


class TestIsNumeric:
    def test_all_numeric(self):
        assert _is_numeric(["1", "2", "3"])

    def test_single_float(self):
        assert _is_numeric(["3.14"])

    def test_all_text(self):
        assert not _is_numeric(["hello", "world"])

    def test_empty_list(self):
        assert not _is_numeric([])

    def test_mixed_mostly_numeric(self):
        # 9 numeric, 1 text  → 90 % → should be True
        assert _is_numeric(["1"] * 9 + ["x"])

    def test_mixed_mostly_text(self):
        # 7 text, 3 numeric → 30 % → should be False
        assert not _is_numeric(["x"] * 7 + ["1", "2", "3"])

    def test_only_whitespace(self):
        assert not _is_numeric(["  ", "\t"])


class TestPercentile:
    def test_median_odd(self):
        assert _percentile([1.0, 2.0, 3.0], 50) == pytest.approx(2.0)

    def test_median_even(self):
        assert _percentile([1.0, 2.0, 3.0, 4.0], 50) == pytest.approx(2.5)

    def test_min(self):
        assert _percentile([1.0, 5.0, 9.0], 0) == pytest.approx(1.0)

    def test_max(self):
        assert _percentile([1.0, 5.0, 9.0], 100) == pytest.approx(9.0)

    def test_empty(self):
        assert _percentile([], 50) == 0.0


# ===========================================================================
# _field_stats
# ===========================================================================

class TestFieldStats:
    def test_numeric_basic(self):
        stats = _field_stats(["1", "2", "3", "4", "5"])
        assert stats["type"] == "numeric"
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["missing"] == 0
        assert stats["unique"] == 5

    def test_numeric_std(self):
        stats = _field_stats(["2", "4", "4", "4", "5", "5", "7", "9"])
        assert "std" in stats
        assert stats["std"] == pytest.approx(2.0)

    def test_numeric_quartiles(self):
        stats = _field_stats([str(i) for i in range(1, 101)])
        assert "q1" in stats
        assert "q3" in stats
        assert stats["q1"] < stats["median"] < stats["q3"]

    def test_categorical_top_values(self):
        values = ["a", "a", "a", "b", "b", "c"]
        stats = _field_stats(values)
        assert stats["type"] == "categorical"
        tops = {v["value"]: v["count"] for v in stats["top_values"]}
        assert tops["a"] == 3
        assert tops["b"] == 2
        assert tops["c"] == 1

    def test_missing_values(self):
        stats = _field_stats(["1", "", "3", ""])
        assert stats["missing"] == 2
        assert stats["missing_pct"] == pytest.approx(50.0)

    def test_all_missing(self):
        stats = _field_stats(["", "", ""])
        assert stats["missing"] == 3
        assert stats["type"] == "categorical"

    def test_single_value(self):
        stats = _field_stats(["42"])
        assert stats["type"] == "numeric"
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["std"] == pytest.approx(0.0)

    def test_top_values_capped_at_five(self):
        # 20 distinct text values → categorical branch, top_values capped at 5
        values = [chr(ord("a") + i) * 3 for i in range(20)]
        stats = _field_stats(values)
        assert stats["type"] == "categorical"
        assert len(stats["top_values"]) <= 5


# ===========================================================================
# DataCard
# ===========================================================================

_SAMPLE_ROWS = [
    {"age": "25", "city": "Paris", "score": "88.5"},
    {"age": "30", "city": "London", "score": "92.0"},
    {"age": "22", "city": "Paris", "score": "76.0"},
    {"age": "35", "city": "Berlin", "score": ""},
]


def _make_card(num_examples: int = 3) -> DataCard:
    gen = DatacardGenerator(
        name="Test Dataset",
        description="A test dataset.",
        license="mit",
        source="https://example.com",
        tags=["test"],
        version="1.0.0",
        num_examples=num_examples,
    )
    return gen.generate_from_dict(_SAMPLE_ROWS)


class TestDataCard:
    def test_basic_attributes(self):
        card = _make_card()
        assert card.name == "Test Dataset"
        assert card.num_rows == 4
        assert card.num_cols == 3

    def test_field_types(self):
        card = _make_card()
        dtypes = {f.name: f.dtype for f in card.fields}
        assert dtypes["age"] == "numeric"
        assert dtypes["city"] == "categorical"
        assert dtypes["score"] == "numeric"

    def test_examples_count(self):
        card = _make_card(num_examples=2)
        assert len(card.examples) == 2

    def test_examples_zero(self):
        card = _make_card(num_examples=0)
        assert card.examples == []

    def test_to_dict_keys(self):
        d = _make_card().to_dict()
        for key in ("name", "description", "num_rows", "num_cols", "license",
                    "source", "version", "tags", "fields"):
            assert key in d

    def test_to_json_valid(self):
        j = _make_card().to_json()
        parsed = json.loads(j)
        assert parsed["name"] == "Test Dataset"
        assert parsed["num_rows"] == 4

    def test_to_markdown_contains_frontmatter(self):
        md = _make_card().to_markdown()
        assert md.startswith("---")
        assert "pretty_name: Test Dataset" in md
        assert "license: mit" in md

    def test_to_markdown_table_valid(self):
        md = _make_card().to_markdown()
        # The stats table must have a proper separator row (no stray `]`)
        assert "|-------|------|---------|--------|" in md
        assert "|-------|------|---------|--------|]" not in md

    def test_to_markdown_has_example_rows(self):
        md = _make_card(num_examples=3).to_markdown()
        assert "## Example Rows" in md
        # Header row must contain field names
        assert "age" in md

    def test_to_markdown_no_example_rows_section_when_zero(self):
        md = _make_card(num_examples=0).to_markdown()
        assert "## Example Rows" not in md

    def test_to_markdown_numeric_quartiles(self):
        md = _make_card().to_markdown()
        assert "Q1 / Q3" in md

    def test_empty_dataset(self):
        gen = DatacardGenerator(name="Empty", description="Nothing here.")
        card = gen.generate_from_dict([])
        assert card.num_rows == 0
        assert card.num_cols == 0
        assert card.to_json()
        assert card.to_markdown()

    def test_tags_in_markdown(self):
        md = _make_card().to_markdown()
        assert "tags:" in md
        assert "  - test" in md


# ===========================================================================
# DatacardGenerator
# ===========================================================================

class TestDatacardGenerator:
    def test_generate_from_dict(self):
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate_from_dict([{"x": "1"}, {"x": "2"}])
        assert card.num_rows == 2
        assert card.num_cols == 1

    def test_generate_from_csv(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("name,value\nalice,10\nbob,20\n", encoding="utf-8")
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate_from_csv(p)
        assert card.num_rows == 2
        assert card.num_cols == 2

    def test_generate_from_csv_via_generate(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate(p)
        assert card.num_rows == 2

    def test_generate_from_json_list(self, tmp_path):
        p = tmp_path / "data.json"
        data = [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}]
        p.write_text(json.dumps(data), encoding="utf-8")
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate_from_json(p)
        assert card.num_rows == 2
        assert card.num_cols == 2

    def test_generate_from_json_column_dict(self, tmp_path):
        p = tmp_path / "data.json"
        data = {"x": [1, 2, 3], "y": ["a", "b", "c"]}
        p.write_text(json.dumps(data), encoding="utf-8")
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate_from_json(p)
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_json_via_generate(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text(json.dumps([{"v": 1}]), encoding="utf-8")
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate(p)
        assert card.num_rows == 1

    def test_generate_column_dict(self):
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate({"x": [1, 2, 3], "y": [4, 5, 6]})
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_unsupported_type_raises(self):
        gen = DatacardGenerator(name="D", description="desc")
        with pytest.raises(TypeError):
            gen.generate(42)

    def test_csv_with_missing_values(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("a,b\n1,\n2,\n3,4\n", encoding="utf-8")
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate_from_csv(p)
        b_field = next(f for f in card.fields if f.name == "b")
        assert b_field.stats["missing"] == 2

    def test_csv_unicode(self, tmp_path):
        p = tmp_path / "data.csv"
        p.write_text("city\nParis\nTokyo\nNairobi\n", encoding="utf-8")
        gen = DatacardGenerator(name="D", description="desc")
        card = gen.generate_from_csv(p)
        assert card.num_rows == 3


# ===========================================================================
# DatacardSchema
# ===========================================================================

class TestDatacardSchema:
    def _valid_dict(self):
        return {
            "name": "My Dataset",
            "description": "A great dataset.",
            "num_rows": 100,
            "license": "mit",
            "version": "1.0.0",
            "tags": ["nlp"],
            "fields": [{"name": "col1", "dtype": "numeric", "stats": {}}],
        }

    def test_valid_card_passes(self):
        schema = DatacardSchema()
        assert schema.is_valid(self._valid_dict())

    def test_missing_name_fails(self):
        d = self._valid_dict()
        d["name"] = ""
        errors = DatacardSchema().validate(d)
        assert any(e.field == "name" for e in errors)

    def test_empty_description_fails(self):
        d = self._valid_dict()
        d["description"] = "  "
        errors = DatacardSchema().validate(d)
        assert any(e.field == "description" for e in errors)

    def test_invalid_license_fails(self):
        d = self._valid_dict()
        d["license"] = "not-a-real-license"
        errors = DatacardSchema().validate(d)
        assert any(e.field == "license" for e in errors)

    def test_unknown_license_passes(self):
        d = self._valid_dict()
        d["license"] = "unknown"
        assert DatacardSchema().is_valid(d)

    def test_negative_num_rows_fails(self):
        d = self._valid_dict()
        d["num_rows"] = -1
        errors = DatacardSchema().validate(d)
        assert any(e.field == "num_rows" for e in errors)

    def test_bad_version_fails(self):
        d = self._valid_dict()
        d["version"] = "v1.0"
        errors = DatacardSchema().validate(d)
        assert any(e.field == "version" for e in errors)

    def test_good_version_passes(self):
        d = self._valid_dict()
        d["version"] = "2.3.1"
        assert DatacardSchema().is_valid(d)

    def test_non_list_tags_fails(self):
        d = self._valid_dict()
        d["tags"] = "nlp"
        errors = DatacardSchema().validate(d)
        assert any(e.field == "tags" for e in errors)

    def test_non_dict_fields_entry_fails(self):
        d = self._valid_dict()
        d["fields"] = ["not-a-dict"]
        errors = DatacardSchema().validate(d)
        assert any("fields" in e.field for e in errors)

    def test_validation_error_str(self):
        e = DatacardSchema().validate({"name": "", "description": "x",
                                       "num_rows": 0, "fields": []})[0]
        assert "[name]" in str(e)

    def test_generated_card_is_valid(self):
        gen = DatacardGenerator(name="Valid", description="A dataset.", license="mit")
        card = gen.generate_from_dict([{"x": "1"}])
        assert DatacardSchema().is_valid(card.to_dict())


# ===========================================================================
# Package-level imports
# ===========================================================================

class TestPackageImports:
    def test_import_main_classes(self):
        import datacard_gen
        assert hasattr(datacard_gen, "DatacardGenerator")
        assert hasattr(datacard_gen, "DataCard")
        assert hasattr(datacard_gen, "DatacardSchema")
        assert hasattr(datacard_gen, "FieldInfo")

    def test_version(self):
        import datacard_gen
        assert datacard_gen.__version__ == "0.1.0"
