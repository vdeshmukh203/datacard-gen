"""Tests for datacard_gen — JOSS submission quality."""
import json
import sys
from pathlib import Path

import pytest

# Ensure the src package is importable when running pytest from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import datacard_gen as dcg
from datacard_gen.generator import (
    DataCard,
    DatacardGenerator,
    FieldInfo,
    _field_stats,
    _is_numeric,
    _safe_float,
)
from datacard_gen.schema import DatacardSchema, ValidationError


# ===========================================================================
# _safe_float
# ===========================================================================

def test_safe_float_integer_string():
    assert _safe_float("42") == 42.0


def test_safe_float_float_string():
    assert _safe_float("3.14") == pytest.approx(3.14)


def test_safe_float_negative():
    assert _safe_float("-7.5") == pytest.approx(-7.5)


def test_safe_float_numeric_type():
    assert _safe_float(1.0) == 1.0


def test_safe_float_non_numeric_string():
    assert _safe_float("hello") is None


def test_safe_float_none():
    assert _safe_float(None) is None


def test_safe_float_empty_string():
    assert _safe_float("") is None


# ===========================================================================
# _is_numeric
# ===========================================================================

def test_is_numeric_all_integers():
    assert _is_numeric(["1", "2", "3"])


def test_is_numeric_all_floats():
    assert _is_numeric(["3.14", "2.71", "1.41"])


def test_is_numeric_all_strings():
    assert not _is_numeric(["apple", "banana", "cherry"])


def test_is_numeric_empty_list():
    assert not _is_numeric([])


def test_is_numeric_all_whitespace():
    assert not _is_numeric(["", "  ", "\t"])


def test_is_numeric_80_percent_threshold_true():
    # 4 out of 5 are numeric → 80 % ≥ threshold → True
    assert _is_numeric(["1", "2", "3", "4", "oops"])


def test_is_numeric_below_80_percent_false():
    # 3 out of 6 are numeric → 50 % < threshold → False
    assert not _is_numeric(["1", "2", "3", "a", "b", "c"])


# ===========================================================================
# _field_stats
# ===========================================================================

def test_field_stats_numeric_basic():
    stats = _field_stats(["1", "2", "3", "4", "5"])
    assert stats["type"] == "numeric"
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["mean"] == pytest.approx(3.0)
    assert stats["missing"] == 0
    assert stats["count"] == 5


def test_field_stats_numeric_std():
    stats = _field_stats(["2", "4", "4", "4", "5", "5", "7", "9"])
    assert stats["std"] == pytest.approx(2.0, abs=0.01)


def test_field_stats_numeric_median_odd():
    stats = _field_stats(["1", "3", "5"])
    assert stats["median"] == 3.0


def test_field_stats_numeric_median_even():
    stats = _field_stats(["1", "2", "3", "4"])
    assert stats["median"] == pytest.approx(2.5)


def test_field_stats_categorical_basic():
    stats = _field_stats(["a", "b", "a", "c", "b", "a"])
    assert stats["type"] == "categorical"
    assert stats["unique"] == 3
    assert stats["top_values"][0]["value"] == "a"
    assert stats["top_values"][0]["count"] == 3


def test_field_stats_categorical_top5_limit():
    # Use alphabetic labels so _is_numeric returns False
    labels = [f"cat_{c}" for c in "abcdefghij"]  # 10 distinct categorical values
    values = labels * 2
    stats = _field_stats(values)
    assert len(stats["top_values"]) == 5


def test_field_stats_missing_values():
    stats = _field_stats(["1", "", "3", ""])
    assert stats["missing"] == 2
    assert stats["missing_pct"] == pytest.approx(50.0)


def test_field_stats_empty_input():
    stats = _field_stats([])
    assert stats["count"] == 0
    assert stats["missing_pct"] == 0.0


def test_field_stats_all_missing():
    stats = _field_stats(["", "", ""])
    assert stats["missing"] == 3
    assert stats["missing_pct"] == pytest.approx(100.0)


# ===========================================================================
# DatacardGenerator.generate_from_dict
# ===========================================================================

def test_generate_from_dict_basic():
    gen = DatacardGenerator(name="TestDS", description="A test.")
    card = gen.generate_from_dict([
        {"x": "1", "label": "a"},
        {"x": "2", "label": "b"},
        {"x": "3", "label": "c"},
    ])
    assert card.num_rows == 3
    assert card.num_cols == 2
    assert card.name == "TestDS"
    assert len(card.fields) == 2


def test_generate_from_dict_empty():
    gen = DatacardGenerator()
    card = gen.generate_from_dict([])
    assert card.num_rows == 0
    assert card.num_cols == 0
    assert card.fields == []


def test_generate_from_dict_numeric_column():
    gen = DatacardGenerator()
    card = gen.generate_from_dict([{"v": 1}, {"v": 2}, {"v": 3}])
    assert card.fields[0].dtype == "numeric"


def test_generate_from_dict_categorical_column():
    gen = DatacardGenerator()
    card = gen.generate_from_dict([{"c": "x"}, {"c": "y"}])
    assert card.fields[0].dtype == "categorical"


# ===========================================================================
# DatacardGenerator.generate_from_csv
# ===========================================================================

def test_generate_from_csv_basic(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("a,b,c\n1,2,x\n3,4,y\n5,6,z\n")
    gen = DatacardGenerator(name="CSV Test")
    card = gen.generate_from_csv(csv_file)
    assert card.num_rows == 3
    assert card.num_cols == 3
    assert card.fields[0].dtype == "numeric"
    assert card.fields[2].dtype == "categorical"


def test_generate_from_csv_utf8(tmp_path):
    csv_file = tmp_path / "unicode.csv"
    csv_file.write_text("city\nPécs\nÉger\nGyőr\n", encoding="utf-8")
    card = DatacardGenerator().generate_from_csv(csv_file)
    assert card.num_rows == 3
    assert card.fields[0].dtype == "categorical"


def test_generate_from_string():
    gen = DatacardGenerator(name="StringDS")
    card = gen.generate_from_string("n,label\n1,a\n2,b\n3,c\n")
    assert card.num_rows == 3
    assert card.num_cols == 2


# ===========================================================================
# DatacardGenerator.generate (dispatch)
# ===========================================================================

def test_generate_dispatch_path(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("n\n1\n2\n3\n")
    card = DatacardGenerator().generate(csv_file)
    assert card.num_rows == 3


def test_generate_dispatch_list_of_dicts():
    card = DatacardGenerator().generate([{"a": 1}, {"a": 2}])
    assert card.num_rows == 2


def test_generate_dispatch_column_oriented_dict():
    card = DatacardGenerator().generate({"x": [1, 2, 3], "y": ["a", "b", "c"]})
    assert card.num_rows == 3
    assert card.num_cols == 2


def test_generate_dispatch_empty_column_dict():
    card = DatacardGenerator().generate({})
    assert card.num_rows == 0


def test_generate_dispatch_unsupported_type():
    with pytest.raises(TypeError):
        DatacardGenerator().generate(42)


# ===========================================================================
# DataCard metadata propagation
# ===========================================================================

def test_metadata_fields_propagate():
    gen = DatacardGenerator(
        name="Meta DS",
        description="Desc.",
        license="mit",
        source="https://example.com",
        tags=["nlp", "text"],
        version="2.3.0",
    )
    card = gen.generate_from_dict([{"a": "x"}])
    assert card.license == "mit"
    assert card.source == "https://example.com"
    assert card.tags == ["nlp", "text"]
    assert card.version == "2.3.0"


# ===========================================================================
# DataCard serialisation — to_dict / to_json
# ===========================================================================

def test_to_dict_has_required_keys():
    card = DatacardGenerator().generate_from_dict([{"a": "1"}])
    d = card.to_dict()
    for key in ("name", "description", "num_rows", "num_cols", "fields",
                "license", "source", "version", "tags"):
        assert key in d


def test_to_json_round_trips():
    card = DatacardGenerator(name="D").generate_from_dict([{"a": "1", "b": "2"}])
    parsed = json.loads(card.to_json())
    assert parsed["num_rows"] == 1
    assert parsed["name"] == "D"
    assert len(parsed["fields"]) == 2


# ===========================================================================
# DataCard.to_markdown
# ===========================================================================

def test_to_markdown_has_yaml_frontmatter():
    card = DatacardGenerator(name="FMTest", license="mit", version="2.0.0",
                              tags=["cv"]).generate_from_dict([{"x": "1"}])
    md = card.to_markdown()
    assert md.startswith("---\n")
    assert "pretty_name: FMTest" in md
    assert "license: mit" in md
    assert "version: 2.0.0" in md
    assert "  - cv" in md


def test_to_markdown_no_stray_bracket():
    card = DatacardGenerator().generate_from_dict([{"x": "1"}])
    md = card.to_markdown()
    for line in md.splitlines():
        if line.startswith("|---"):
            assert "]" not in line, f"Stray ']' in separator: {line!r}"


def test_to_markdown_source_absent_when_empty():
    card = DatacardGenerator(source="").generate_from_dict([{"x": "1"}])
    assert "**Source:**" not in card.to_markdown()


def test_to_markdown_source_present():
    card = DatacardGenerator(source="https://data.gov").generate_from_dict([{"x": "1"}])
    assert "https://data.gov" in card.to_markdown()


def test_to_markdown_numeric_stats_present():
    card = DatacardGenerator().generate_from_dict(
        [{"v": str(i)} for i in range(10)]
    )
    md = card.to_markdown()
    assert "**Min:**" in md
    assert "**Mean:**" in md
    assert "**Std:**" in md


def test_to_markdown_top_values_present():
    card = DatacardGenerator().generate_from_dict(
        [{"cat": c} for c in ["a", "b", "a", "c", "a"]]
    )
    md = card.to_markdown()
    assert "**Top values:**" in md


def test_to_markdown_row_count_formatted():
    rows = [{"v": str(i)} for i in range(1500)]
    card = DatacardGenerator().generate_from_dict(rows)
    assert "1,500" in card.to_markdown()


# ===========================================================================
# DatacardSchema
# ===========================================================================

def test_schema_validate_valid_card():
    card = DatacardGenerator(name="S", license="mit").generate_from_dict([{"a": "1"}])
    assert DatacardSchema.validate(card.to_dict()) == []


def test_schema_invalid_license():
    card = DatacardGenerator(name="S", license="proprietary-xyz").generate_from_dict(
        [{"a": "1"}]
    )
    warnings = DatacardSchema.validate(card.to_dict())
    assert any("license" in w.lower() or "License" in w for w in warnings)


def test_schema_missing_required_name():
    d = {"description": "hi", "num_rows": 1, "num_cols": 1, "fields": []}
    warnings = DatacardSchema.validate(d)
    assert any("name" in w for w in warnings)


def test_schema_missing_multiple_fields():
    warnings = DatacardSchema.validate({})
    required = {"name", "description", "num_rows", "num_cols", "fields"}
    reported = {w.split("'")[1] for w in warnings if "Missing required field" in w}
    assert required == reported


def test_schema_negative_num_rows():
    d = {"name": "x", "description": "y", "num_rows": -1, "num_cols": 1, "fields": []}
    warnings = DatacardSchema.validate(d)
    assert any("num_rows" in w for w in warnings)


def test_schema_field_missing_name():
    d = {
        "name": "x", "description": "y", "num_rows": 1, "num_cols": 1,
        "fields": [{"dtype": "numeric", "stats": {}}],
    }
    warnings = DatacardSchema.validate(d)
    assert any("missing 'name'" in w for w in warnings)


def test_schema_validate_strict_passes_on_valid():
    card = DatacardGenerator(name="S", license="cc0-1.0").generate_from_dict([{"a": "1"}])
    DatacardSchema.validate_strict(card.to_dict())  # must not raise


def test_schema_validate_strict_raises_on_invalid():
    with pytest.raises(ValidationError):
        DatacardSchema.validate_strict({})


# ===========================================================================
# CLI
# ===========================================================================

def test_cli_csv_markdown(tmp_path):
    from datacard_gen.cli import main

    csv_file = tmp_path / "data.csv"
    csv_file.write_text("a,b\n1,x\n2,y\n")
    out_file = tmp_path / "card.md"
    assert main([str(csv_file), "--name", "CLI Test", "--output", str(out_file)]) == 0
    content = out_file.read_text()
    assert "CLI Test" in content
    assert "# CLI Test" in content


def test_cli_json_output(tmp_path):
    from datacard_gen.cli import main

    csv_file = tmp_path / "data.csv"
    csv_file.write_text("n\n1\n2\n3\n")
    out_file = tmp_path / "card.json"
    assert main([str(csv_file), "--format", "json", "--output", str(out_file)]) == 0
    parsed = json.loads(out_file.read_text())
    assert parsed["num_rows"] == 3


def test_cli_missing_file(tmp_path):
    from datacard_gen.cli import main

    rc = main([str(tmp_path / "nonexistent.csv")])
    assert rc == 1


def test_cli_tags_and_license(tmp_path):
    from datacard_gen.cli import main

    csv_file = tmp_path / "data.csv"
    csv_file.write_text("x\n1\n2\n")
    out_file = tmp_path / "card.md"
    assert main([
        str(csv_file),
        "--tags", "nlp,text",
        "--license", "cc0-1.0",
        "--output", str(out_file),
    ]) == 0
    content = out_file.read_text()
    assert "cc0-1.0" in content
    assert "nlp" in content


def test_cli_validate_flag(tmp_path, capsys):
    from datacard_gen.cli import main

    csv_file = tmp_path / "data.csv"
    csv_file.write_text("x\n1\n")
    assert main([str(csv_file), "--validate", "--license", "mit"]) == 0


# ===========================================================================
# Public API surface (import smoke tests)
# ===========================================================================

def test_public_api_exports():
    assert hasattr(dcg, "DatacardGenerator")
    assert hasattr(dcg, "DataCard")
    assert hasattr(dcg, "FieldInfo")
    assert hasattr(dcg, "DatacardSchema")
    assert hasattr(dcg, "ValidationError")
    assert hasattr(dcg, "__version__")


def test_version_string_format():
    parts = dcg.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
