"""
Tests for datacard_gen — JOSS-level coverage.

Covers: helpers, field stats, DataCard serialisation, DatacardGenerator API,
CLI (stdout + file output), and the markdown table well-formedness fix.
"""

import csv
import io
import json
import pathlib
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
import datacard_gen as dcg


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_valid_int(self):
        assert dcg._safe_float("42") == 42.0

    def test_valid_float(self):
        assert dcg._safe_float("3.14") == pytest.approx(3.14)

    def test_negative(self):
        assert dcg._safe_float("-7.5") == pytest.approx(-7.5)

    def test_non_numeric_returns_none(self):
        assert dcg._safe_float("hello") is None

    def test_none_returns_none(self):
        assert dcg._safe_float(None) is None

    def test_empty_string_returns_none(self):
        assert dcg._safe_float("") is None


class TestIsNumeric:
    def test_all_numeric(self):
        assert dcg._is_numeric(["1", "2", "3.5"])

    def test_all_non_numeric(self):
        assert not dcg._is_numeric(["apple", "banana"])

    def test_empty_list(self):
        assert not dcg._is_numeric([])

    def test_all_whitespace(self):
        assert not dcg._is_numeric(["  ", "\t"])

    def test_mixed_mostly_numeric(self):
        # 9 out of 10 are numeric → meets 80 % threshold
        values = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "cat"]
        assert dcg._is_numeric(values)

    def test_mixed_below_threshold(self):
        # 7 out of 10 numeric → below threshold
        values = ["1", "2", "3", "4", "5", "6", "7", "a", "b", "c"]
        assert not dcg._is_numeric(values)


# ---------------------------------------------------------------------------
# Field statistics
# ---------------------------------------------------------------------------

class TestFieldStats:
    def test_numeric_stats_keys(self):
        stats = dcg._field_stats(["1.0", "2.0", "3.0"])
        for key in ("count", "missing", "missing_pct", "unique", "min", "max", "mean", "std", "median"):
            assert key in stats, f"missing key: {key}"

    def test_numeric_values(self):
        stats = dcg._field_stats(["1", "2", "3", "4", "5"])
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["mean"] == pytest.approx(3.0)
        assert stats["median"] == 3.0

    def test_categorical_stats_keys(self):
        stats = dcg._field_stats(["a", "b", "a", "c"])
        for key in ("count", "missing", "missing_pct", "unique", "top_values"):
            assert key in stats, f"missing key: {key}"

    def test_categorical_top_values_order(self):
        stats = dcg._field_stats(["a", "a", "a", "b", "b", "c"])
        top = stats["top_values"]
        assert top[0]["value"] == "a"
        assert top[0]["count"] == 3

    def test_categorical_top_values_capped_at_5(self):
        # use clearly non-numeric values so the field is treated as categorical
        values = [f"cat_{i}" for i in range(10)]  # 10 distinct string values
        stats = dcg._field_stats(values)
        assert len(stats["top_values"]) <= 5

    def test_missing_counted(self):
        stats = dcg._field_stats(["1", "", "3", "  "])
        assert stats["missing"] == 2
        assert stats["missing_pct"] == pytest.approx(50.0)

    def test_all_missing(self):
        stats = dcg._field_stats(["", "  ", ""])
        assert stats["missing"] == 3
        assert stats["missing_pct"] == pytest.approx(100.0)

    def test_std_non_negative(self):
        stats = dcg._field_stats(["5", "5", "5"])
        assert stats["std"] == pytest.approx(0.0)

    def test_unique_count(self):
        stats = dcg._field_stats(["a", "a", "b"])
        assert stats["unique"] == 2


# ---------------------------------------------------------------------------
# DataCard serialisation
# ---------------------------------------------------------------------------

SAMPLE_ROWS = [
    {"age": "25", "city": "London"},
    {"age": "30", "city": "Paris"},
    {"age": "25", "city": "London"},
]


def _make_card() -> dcg.DataCard:
    gen = dcg.DatacardGenerator(name="Test", description="Desc", license="mit")
    return gen.generate_from_dict(SAMPLE_ROWS)


class TestDataCardToDict:
    def test_keys_present(self):
        d = _make_card().to_dict()
        for k in ("name", "description", "num_rows", "num_cols", "fields", "license"):
            assert k in d

    def test_row_count(self):
        assert _make_card().to_dict()["num_rows"] == 3

    def test_col_count(self):
        assert _make_card().to_dict()["num_cols"] == 2


class TestDataCardToJson:
    def test_valid_json(self):
        j = _make_card().to_json()
        parsed = json.loads(j)
        assert parsed["name"] == "Test"

    def test_fields_in_json(self):
        parsed = json.loads(_make_card().to_json())
        field_names = [f["name"] for f in parsed["fields"]]
        assert "age" in field_names
        assert "city" in field_names


class TestDataCardToMarkdown:
    def _md(self) -> str:
        return _make_card().to_markdown()

    def test_yaml_frontmatter_present(self):
        md = self._md()
        assert md.startswith("---")

    def test_dataset_name_heading(self):
        assert "# Test" in self._md()

    def test_data_fields_section(self):
        assert "## Data Fields" in self._md()

    def test_table_separator_no_stray_bracket(self):
        # Regression: old code had "|-------|------|---------|--------|]"
        for line in self._md().splitlines():
            if line.startswith("|---"):
                assert not line.endswith("]"), (
                    f"Stray ']' found in table separator: {line!r}"
                )

    def test_table_rows_present(self):
        md = self._md()
        assert "| age |" in md or "age" in md

    def test_license_section(self):
        assert "## License" in self._md()
        assert "mit" in self._md()


# ---------------------------------------------------------------------------
# DatacardGenerator API
# ---------------------------------------------------------------------------

class TestDatacardGenerator:
    def test_generate_from_dict(self):
        gen = dcg.DatacardGenerator(name="DS")
        card = gen.generate_from_dict(SAMPLE_ROWS)
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_from_dict_empty(self):
        gen = dcg.DatacardGenerator()
        card = gen.generate_from_dict([])
        assert card.num_rows == 0
        assert card.num_cols == 0

    def test_generate_from_csv(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x,y\n1,a\n2,b\n3,c\n", encoding="utf-8")
        gen = dcg.DatacardGenerator(name="CSV DS")
        card = gen.generate_from_csv(csv_file)
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_polymorphic_path(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("v\n10\n20\n", encoding="utf-8")
        gen = dcg.DatacardGenerator()
        card = gen.generate(csv_file)
        assert card.num_rows == 2

    def test_generate_polymorphic_list(self):
        gen = dcg.DatacardGenerator()
        card = gen.generate(SAMPLE_ROWS)
        assert card.num_rows == 3

    def test_generate_polymorphic_column_dict(self):
        gen = dcg.DatacardGenerator()
        card = gen.generate({"x": [1, 2, 3], "y": ["a", "b", "c"]})
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_unsupported_type_raises(self):
        gen = dcg.DatacardGenerator()
        with pytest.raises(TypeError):
            gen.generate(42)

    def test_tags_stored(self):
        gen = dcg.DatacardGenerator(tags=["nlp", "benchmark"])
        card = gen.generate_from_dict(SAMPLE_ROWS)
        assert "nlp" in card.tags

    def test_version_stored(self):
        gen = dcg.DatacardGenerator(version="2.0.0")
        card = gen.generate_from_dict(SAMPLE_ROWS)
        assert card.version == "2.0.0"

    def test_numeric_field_detected(self):
        gen = dcg.DatacardGenerator()
        card = gen.generate_from_dict([{"score": "0.9"}, {"score": "0.7"}])
        age_field = next(f for f in card.fields if f.name == "score")
        assert age_field.dtype == "numeric"

    def test_categorical_field_detected(self):
        gen = dcg.DatacardGenerator()
        card = gen.generate_from_dict([{"label": "cat"}, {"label": "dog"}])
        label_field = next(f for f in card.fields if f.name == "label")
        assert label_field.dtype == "categorical"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_markdown_stdout(self, tmp_path, capsys):
        csv_file = tmp_path / "sample.csv"
        csv_file.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
        rc = dcg.main([str(csv_file)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "# sample" in out
        assert "## Dataset Structure" in out

    def test_cli_json_stdout(self, tmp_path, capsys):
        csv_file = tmp_path / "sample.csv"
        csv_file.write_text("n\n10\n20\n", encoding="utf-8")
        rc = dcg.main([str(csv_file), "--format", "json"])
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["num_rows"] == 2

    def test_cli_output_file(self, tmp_path, capsys):
        csv_file = tmp_path / "ds.csv"
        out_file = tmp_path / "card.md"
        csv_file.write_text("col\nval\n", encoding="utf-8")
        rc = dcg.main([str(csv_file), "-o", str(out_file)])
        assert rc == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "## Dataset Description" in content

    def test_cli_missing_file_returns_1(self, capsys):
        rc = dcg.main(["nonexistent_file_xyz.csv"])
        assert rc == 1

    def test_cli_custom_name(self, tmp_path, capsys):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x\n1\n", encoding="utf-8")
        rc = dcg.main([str(csv_file), "--name", "MySpecialDS"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "MySpecialDS" in out

    def test_cli_tags_parsed(self, tmp_path, capsys):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x\n1\n", encoding="utf-8")
        rc = dcg.main([str(csv_file), "--tags", "nlp,benchmark"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "nlp" in out


# ---------------------------------------------------------------------------
# Module-level attributes
# ---------------------------------------------------------------------------

def test_version_attribute():
    assert hasattr(dcg, "__version__")
    assert isinstance(dcg.__version__, str)


def test_all_exports():
    for name in dcg.__all__:
        assert hasattr(dcg, name), f"__all__ lists {name!r} but it is not defined"


def test_cli_alias():
    assert dcg._cli is dcg.main
