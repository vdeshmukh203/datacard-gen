"""Tests for datacard_gen."""
import io
import json
import math
import sys
import pathlib
import tempfile
import csv

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import datacard_gen as dcg


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _gen(**kw) -> dcg.DatacardGenerator:
    return dcg.DatacardGenerator(name="test", description="desc.", **kw)


def _csv_file(rows, tmp_path):
    """Write *rows* (list of dicts) to a temp CSV and return the Path."""
    p = pathlib.Path(tmp_path) / "data.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return p


# ---------------------------------------------------------------------------
# Import surface
# ---------------------------------------------------------------------------

def test_import():
    assert hasattr(dcg, "DatacardGenerator")
    assert hasattr(dcg, "DataCard")
    assert hasattr(dcg, "FieldInfo")
    assert hasattr(dcg, "__version__")


def test_cli_alias():
    assert dcg._cli is dcg.main


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

def test_safe_float_valid():
    assert dcg._safe_float("1.5") == 1.5


def test_safe_float_invalid():
    assert dcg._safe_float("bad") is None


def test_safe_float_none():
    assert dcg._safe_float(None) is None


def test_safe_float_integer_string():
    assert dcg._safe_float("42") == 42.0


# ---------------------------------------------------------------------------
# _is_numeric
# ---------------------------------------------------------------------------

def test_is_numeric_true():
    assert dcg._is_numeric(["3.14"])


def test_is_numeric_false():
    assert not dcg._is_numeric(["hello"])


def test_is_numeric_empty():
    assert not dcg._is_numeric([])


def test_is_numeric_all_empty():
    assert not dcg._is_numeric(["", "  "])


def test_is_numeric_mixed_mostly_numeric():
    # 9 numbers, 1 string → 90 % numeric → True
    assert dcg._is_numeric(["1"] * 9 + ["x"])


def test_is_numeric_mixed_mostly_text():
    # 2 numbers, 8 strings → 20 % numeric → False
    assert not dcg._is_numeric(["1", "2"] + ["x"] * 8)


# ---------------------------------------------------------------------------
# _field_stats
# ---------------------------------------------------------------------------

def test_field_stats_numeric():
    stats = dcg._field_stats(["1", "2", "3", "4", "5"])
    assert stats["type"] == "numeric"
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert math.isclose(stats["mean"], 3.0)
    assert stats["median"] == 3.0
    assert stats["missing"] == 0
    assert stats["unique"] == 5


def test_field_stats_numeric_missing():
    stats = dcg._field_stats(["1", "", "3"])
    assert stats["missing"] == 1
    assert math.isclose(stats["missing_pct"], 33.33)


def test_field_stats_categorical():
    stats = dcg._field_stats(["a", "b", "a", "c", "a"])
    assert stats["type"] == "categorical"
    top = {v["value"]: v["count"] for v in stats["top_values"]}
    assert top["a"] == 3
    assert stats["unique"] == 3


def test_field_stats_all_missing():
    stats = dcg._field_stats(["", " ", ""])
    assert stats["missing_pct"] == 100.0


def test_field_stats_empty_list():
    stats = dcg._field_stats([])
    assert stats["count"] == 0
    assert stats["missing_pct"] == 0.0


# ---------------------------------------------------------------------------
# DataCard serialisation
# ---------------------------------------------------------------------------

def test_to_dict_roundtrip():
    fi = dcg.FieldInfo(name="x", dtype="numeric", stats={"min": 0, "max": 1})
    card = dcg.DataCard(
        name="ds", description="d", num_rows=10, num_cols=1,
        fields=[fi], license="mit", version="2.0.0",
    )
    d = card.to_dict()
    assert d["name"] == "ds"
    assert d["num_rows"] == 10
    assert d["fields"][0]["name"] == "x"


def test_to_json_valid():
    card = dcg.DataCard(name="ds", description="d", num_rows=1, num_cols=0)
    parsed = json.loads(card.to_json())
    assert parsed["name"] == "ds"


def test_to_markdown_contains_yaml_frontmatter():
    card = dcg.DataCard(name="iris", description="d", num_rows=150, num_cols=4,
                        license="cc0-1.0", tags=["tabular"])
    md = card.to_markdown()
    assert md.startswith("---\n")
    assert "pretty_name: iris" in md
    assert "license: cc0-1.0" in md
    assert "  - tabular" in md


def test_to_markdown_no_broken_table():
    card = dcg.DataCard(
        name="t", description="d", num_rows=2, num_cols=1,
        fields=[dcg.FieldInfo("col", "numeric", {"min": 0, "max": 1,
                                                   "mean": 0.5, "std": 0.5,
                                                   "median": 0.5, "missing": 0,
                                                   "missing_pct": 0.0, "unique": 2})],
    )
    md = card.to_markdown()
    # The separator row must NOT contain a stray closing bracket
    for line in md.splitlines():
        if line.startswith("|---"):
            assert "]" not in line, f"Broken table separator: {line!r}"


def test_to_markdown_numeric_stats_shown():
    fi = dcg.FieldInfo("score", "numeric", {
        "min": 0.0, "max": 100.0, "mean": 50.0,
        "std": 10.0, "median": 50.0,
        "missing": 0, "missing_pct": 0.0, "unique": 10,
    })
    card = dcg.DataCard(name="t", description="d", num_rows=10, num_cols=1, fields=[fi])
    md = card.to_markdown()
    assert "**Min:** 0.0" in md
    assert "**Mean:** 50.0" in md


def test_to_markdown_categorical_top_values():
    fi = dcg.FieldInfo("cat", "categorical", {
        "top_values": [{"value": "A", "count": 5}],
        "missing": 0, "missing_pct": 0.0, "unique": 1,
    })
    card = dcg.DataCard(name="t", description="d", num_rows=5, num_cols=1, fields=[fi])
    md = card.to_markdown()
    assert "A (5)" in md


# ---------------------------------------------------------------------------
# DatacardGenerator — in-memory inputs
# ---------------------------------------------------------------------------

def test_generate_from_dict_basic():
    data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    card = _gen().generate_from_dict(data)
    assert card.num_rows == 2
    assert card.num_cols == 2
    assert card.fields[0].dtype == "numeric"
    assert card.fields[1].dtype == "categorical"


def test_generate_empty_dict():
    card = _gen().generate_from_dict([])
    assert card.num_rows == 0
    assert card.num_cols == 0


def test_generate_columnar_dict():
    data = {"x": [1, 2, 3], "y": ["a", "b", "c"]}
    card = _gen().generate(data)
    assert card.num_rows == 3
    assert card.num_cols == 2


def test_generate_columnar_dict_unequal_raises():
    import pytest
    with pytest.raises(ValueError, match="unequal length"):
        _gen().generate({"x": [1, 2], "y": [1]})


def test_generate_unsupported_type_raises():
    import pytest
    with pytest.raises(TypeError):
        _gen().generate(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DatacardGenerator — CSV files
# ---------------------------------------------------------------------------

def test_generate_from_csv(tmp_path):
    rows = [{"age": "25", "name": "Alice"}, {"age": "30", "name": "Bob"}]
    p = _csv_file(rows, tmp_path)
    card = _gen().generate_from_csv(p)
    assert card.num_rows == 2
    assert card.num_cols == 2


def test_generate_from_csv_not_found():
    import pytest
    with pytest.raises(FileNotFoundError):
        _gen().generate_from_csv("/nonexistent/file.csv")


def test_generate_csv_via_generate(tmp_path):
    rows = [{"v": "1"}, {"v": "2"}]
    p = _csv_file(rows, tmp_path)
    card = _gen().generate(p)
    assert card.num_rows == 2


def test_generate_csv_via_generate_string_path(tmp_path):
    rows = [{"v": "1"}]
    p = _csv_file(rows, tmp_path)
    card = _gen().generate(str(p))
    assert card.num_rows == 1


# ---------------------------------------------------------------------------
# DatacardGenerator — JSON files
# ---------------------------------------------------------------------------

def test_generate_from_json(tmp_path):
    data = [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}]
    p = pathlib.Path(tmp_path) / "data.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    card = _gen().generate_from_json(p)
    assert card.num_rows == 2


def test_generate_from_json_not_found():
    import pytest
    with pytest.raises(FileNotFoundError):
        _gen().generate_from_json("/nonexistent/file.json")


def test_generate_from_json_not_a_list(tmp_path):
    import pytest
    p = pathlib.Path(tmp_path) / "bad.json"
    p.write_text(json.dumps({"key": "val"}), encoding="utf-8")
    with pytest.raises(ValueError, match="array"):
        _gen().generate_from_json(p)


def test_generate_json_via_generate(tmp_path):
    data = [{"n": 3}]
    p = pathlib.Path(tmp_path) / "data.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    card = _gen().generate(p)
    assert card.num_rows == 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_csv(tmp_path):
    rows = [{"a": "1", "b": "hello"}]
    p = _csv_file(rows, tmp_path)
    rc = dcg.main([str(p), "--format", "json"])
    assert rc == 0


def test_cli_missing_file(tmp_path, capsys):
    rc = dcg.main([str(tmp_path / "missing.csv")])
    assert rc == 1


def test_cli_markdown_output(tmp_path):
    rows = [{"score": "10"}, {"score": "20"}]
    p = _csv_file(rows, tmp_path)
    out_file = tmp_path / "card.md"
    rc = dcg.main([str(p), "--format", "markdown", "--output", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "# data" in content


def test_cli_tags_parsed(tmp_path):
    rows = [{"x": "1"}]
    p = _csv_file(rows, tmp_path)
    out = tmp_path / "card.json"
    dcg.main([str(p), "--tags", "ml, cv", "--format", "json", "--output", str(out)])
    d = json.loads(out.read_text())
    assert "ml" in d["tags"]
    assert "cv" in d["tags"]
