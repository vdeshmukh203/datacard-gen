"""Tests for datacard_gen — the automated dataset card generator."""

import json
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so the single-file module is found.
sys.path.insert(0, str(Path(__file__).parent.parent))

import datacard_gen as dcg


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

def test_safe_float_valid_string():
    assert dcg._safe_float("1.5") == 1.5


def test_safe_float_valid_int():
    assert dcg._safe_float(42) == 42.0


def test_safe_float_zero():
    assert dcg._safe_float("0") == 0.0


def test_safe_float_invalid():
    assert dcg._safe_float("bad") is None


def test_safe_float_none():
    assert dcg._safe_float(None) is None


def test_safe_float_empty():
    assert dcg._safe_float("") is None


# ---------------------------------------------------------------------------
# _is_numeric
# ---------------------------------------------------------------------------

def test_is_numeric_true():
    assert dcg._is_numeric(["1", "2", "3.14"])


def test_is_numeric_false():
    assert not dcg._is_numeric(["hello", "world"])


def test_is_numeric_empty_list():
    assert not dcg._is_numeric([])


def test_is_numeric_all_empty_strings():
    assert not dcg._is_numeric(["", "   "])


def test_is_numeric_exactly_80_pct():
    # 4 numeric out of 5 = 80% — boundary case, should be True
    assert dcg._is_numeric(["1", "2", "3", "4", "text"])


def test_is_numeric_below_threshold():
    # 2 numeric out of 5 = 40% — should be False
    assert not dcg._is_numeric(["1", "2", "text", "more", "words"])


# ---------------------------------------------------------------------------
# _field_stats
# ---------------------------------------------------------------------------

def test_field_stats_numeric_basic():
    stats = dcg._field_stats(["1", "2", "3", "4", "5"])
    assert stats["type"] == "numeric"
    assert stats["count"] == 5
    assert stats["missing"] == 0
    assert stats["missing_pct"] == 0.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["mean"] == 3.0
    assert stats["median"] == 3.0
    assert "std" in stats


def test_field_stats_numeric_with_missing():
    stats = dcg._field_stats(["1", "", "3"])
    assert stats["missing"] == 1
    assert stats["missing_pct"] > 0
    assert stats["type"] == "numeric"


def test_field_stats_categorical():
    stats = dcg._field_stats(["a", "b", "a", "c", "a"])
    assert stats["type"] == "categorical"
    assert stats["count"] == 5
    assert stats["unique"] == 3
    top = stats["top_values"]
    assert top[0]["value"] == "a"
    assert top[0]["count"] == 3


def test_field_stats_categorical_top_values_capped_at_5():
    values = [str(i) for i in range(20)]  # 20 unique strings
    # Prepend some repeated values to make them rank highly
    values = ["z"] * 6 + ["y"] * 5 + ["x"] * 4 + ["w"] * 3 + ["v"] * 2 + values
    stats = dcg._field_stats(values)
    assert stats["type"] == "categorical"
    assert len(stats["top_values"]) <= 5


def test_field_stats_empty():
    stats = dcg._field_stats([])
    assert stats["count"] == 0
    assert stats["missing_pct"] == 0.0


def test_field_stats_all_missing():
    stats = dcg._field_stats(["", "   ", ""])
    assert stats["missing"] == 3
    assert stats["missing_pct"] == 100.0


def test_field_stats_median_even_count():
    # Even number of elements: median is average of two middle values
    stats = dcg._field_stats(["1", "2", "3", "4"])
    assert stats["median"] == 2.5


def test_field_stats_std_nonnegative():
    stats = dcg._field_stats(["5", "5", "5"])
    assert stats["std"] == 0.0


# ---------------------------------------------------------------------------
# FieldInfo
# ---------------------------------------------------------------------------

def test_field_info_to_dict():
    fi = dcg.FieldInfo(name="age", dtype="numeric", stats={"min": 1, "max": 100})
    d = fi.to_dict()
    assert d["name"] == "age"
    assert d["dtype"] == "numeric"
    assert d["stats"]["min"] == 1


# ---------------------------------------------------------------------------
# DataCard
# ---------------------------------------------------------------------------

def test_datacard_to_dict_keys():
    card = dcg.DataCard(
        name="Test", description="Desc", num_rows=10, num_cols=2,
        license="MIT", tags=["ml"],
    )
    d = card.to_dict()
    for key in ("name", "description", "num_rows", "num_cols", "license",
                "source", "version", "tags", "fields"):
        assert key in d


def test_datacard_to_json_valid():
    card = dcg.DataCard(name="Test", description="Desc", num_rows=3, num_cols=1)
    parsed = json.loads(card.to_json())
    assert parsed["name"] == "Test"
    assert parsed["num_rows"] == 3


def test_datacard_to_markdown_sections():
    card = dcg.DataCard(
        name="MyData", description="A test dataset.", num_rows=100, num_cols=3,
        license="cc-by-4.0", tags=["nlp"],
    )
    md = card.to_markdown()
    for section in (
        "# MyData",
        "## Dataset Description",
        "## Dataset Structure",
        "## Data Fields",
        "## Dataset Statistics",
        "## License",
        "cc-by-4.0",
    ):
        assert section in md, f"Missing section: {section!r}"


def test_datacard_markdown_table_separator_no_stray_chars():
    """Regression: ensure the stats table separator row is well-formed."""
    card = dcg.DataCard(name="X", description="D", num_rows=1, num_cols=1)
    for line in card.to_markdown().splitlines():
        if line.startswith("|---"):
            assert line.endswith("|"), (
                f"Table separator has invalid ending: {line!r}"
            )


def test_datacard_markdown_yaml_frontmatter():
    card = dcg.DataCard(
        name="MyDS", description="D", num_rows=5, num_cols=2,
        license="MIT", version="2.0.0", tags=["vision"],
    )
    lines = card.to_markdown().splitlines()
    assert lines[0] == "---", "Markdown must start with YAML frontmatter '---'"
    assert any("license: MIT" in l for l in lines)
    assert any("version: 2.0.0" in l for l in lines)
    assert any("- vision" in l for l in lines)


def test_datacard_markdown_numeric_field_stats():
    fi = dcg.FieldInfo(
        name="score", dtype="numeric",
        stats={"missing": 0, "missing_pct": 0.0, "unique": 10,
               "min": 1.0, "max": 100.0, "mean": 50.0, "std": 10.0, "median": 50.0},
    )
    card = dcg.DataCard(name="DS", description="D", num_rows=10, num_cols=1, fields=[fi])
    md = card.to_markdown()
    assert "**Min:**" in md
    assert "**Max:**" in md
    assert "**Mean:**" in md


def test_datacard_markdown_categorical_field_top_values():
    fi = dcg.FieldInfo(
        name="label", dtype="categorical",
        stats={"missing": 0, "missing_pct": 0.0, "unique": 2,
               "top_values": [{"value": "yes", "count": 7}, {"value": "no", "count": 3}]},
    )
    card = dcg.DataCard(name="DS", description="D", num_rows=10, num_cols=1, fields=[fi])
    md = card.to_markdown()
    assert "**Top values:**" in md
    assert "yes" in md


# ---------------------------------------------------------------------------
# DatacardGenerator
# ---------------------------------------------------------------------------

def test_generator_from_dict_basic():
    data = [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}, {"x": 3, "y": "c"}]
    card = dcg.DatacardGenerator(name="TestDS").generate_from_dict(data)
    assert card.name == "TestDS"
    assert card.num_rows == 3
    assert card.num_cols == 2


def test_generator_field_dtype_inference():
    data = [{"num": "1.5", "cat": "hello"}] * 10
    card = dcg.DatacardGenerator().generate_from_dict(data)
    dtype_map = {f.name: f.dtype for f in card.fields}
    assert dtype_map["num"] == "numeric"
    assert dtype_map["cat"] == "categorical"


def test_generator_from_column_dict():
    data = {"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]}
    card = dcg.DatacardGenerator().generate(data)
    assert card.num_rows == 3
    assert card.num_cols == 2


def test_generator_column_dict_unequal_lengths():
    with pytest.raises(ValueError, match="equal-length"):
        dcg.DatacardGenerator().generate({"a": [1, 2], "b": [1, 2, 3]})


def test_generator_empty_list():
    card = dcg.DatacardGenerator(name="Empty").generate([])
    assert card.num_rows == 0
    assert card.num_cols == 0


def test_generator_empty_dict():
    card = dcg.DatacardGenerator().generate({})
    assert card.num_rows == 0


def test_generator_from_csv(tmp_path):
    f = tmp_path / "sample.csv"
    f.write_text("name,score\nAlice,90\nBob,85\nCarol,92\n", encoding="utf-8")
    card = dcg.DatacardGenerator(name="scores").generate_from_csv(f)
    assert card.num_rows == 3
    assert card.num_cols == 2
    dtype_map = {fi.name: fi.dtype for fi in card.fields}
    assert dtype_map["score"] == "numeric"
    assert dtype_map["name"] == "categorical"


def test_generator_from_json_row_oriented(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]), encoding="utf-8")
    card = dcg.DatacardGenerator(name="json_ds").generate_from_json(f)
    assert card.num_rows == 2
    assert card.num_cols == 2


def test_generator_from_json_column_oriented(tmp_path):
    f = tmp_path / "col.json"
    f.write_text(json.dumps({"x": [10, 20, 30], "y": ["a", "b", "c"]}), encoding="utf-8")
    card = dcg.DatacardGenerator().generate_from_json(f)
    assert card.num_rows == 3
    assert card.num_cols == 2


def test_generator_from_json_invalid_type(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text('"just a string"', encoding="utf-8")
    with pytest.raises(ValueError):
        dcg.DatacardGenerator().generate_from_json(f)


def test_generator_generate_dispatches_csv(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("v\n1\n2\n", encoding="utf-8")
    assert dcg.DatacardGenerator().generate(f).num_rows == 2


def test_generator_generate_dispatches_json(tmp_path):
    f = tmp_path / "d.json"
    f.write_text('[{"v": 1}, {"v": 2}]', encoding="utf-8")
    assert dcg.DatacardGenerator().generate(f).num_rows == 2


def test_generator_generate_string_path(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("a\n1\n2\n", encoding="utf-8")
    assert dcg.DatacardGenerator().generate(str(f)).num_rows == 2


def test_generator_file_not_found():
    with pytest.raises(FileNotFoundError):
        dcg.DatacardGenerator().generate("/nonexistent/path.csv")


def test_generator_unsupported_type():
    with pytest.raises(TypeError):
        dcg.DatacardGenerator().generate(42)  # type: ignore[arg-type]


def test_generator_metadata_propagated():
    card = dcg.DatacardGenerator(
        name="DS", description="Desc", license="MIT",
        source="https://example.com", tags=["a", "b"], version="2.0",
    ).generate([{"x": "1"}])
    assert card.name == "DS"
    assert card.license == "MIT"
    assert card.source == "https://example.com"
    assert card.tags == ["a", "b"]
    assert card.version == "2.0"


# ---------------------------------------------------------------------------
# CLI (main / _cli)
# ---------------------------------------------------------------------------

def test_cli_csv_returns_zero(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("x,y\n1,a\n2,b\n", encoding="utf-8")
    assert dcg.main([str(f), "--format", "markdown"]) == 0


def test_cli_json_format_returns_zero(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("x\n1\n2\n", encoding="utf-8")
    assert dcg.main([str(f), "--format", "json", "--name", "myds"]) == 0


def test_cli_missing_file_returns_one():
    assert dcg.main(["/no/such/file.csv"]) == 1


def test_cli_output_file(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
    out = tmp_path / "card.md"
    assert dcg.main([str(f), "-o", str(out)]) == 0
    assert out.is_file()
    assert "# t" in out.read_text(encoding="utf-8")


def test_cli_alias_is_main():
    assert dcg._cli is dcg.main
