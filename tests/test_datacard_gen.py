"""Tests for datacard_gen (root-level standalone module)."""
import csv
import io
import json
import math
import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so we import the standalone module.
sys.path.insert(0, str(Path(__file__).parent.parent))
import datacard_gen as dcg


# ── Helpers ───────────────────────────────────────────────────────────────── #

def _write_csv(tmp_path: Path, rows: list, filename: str = "data.csv") -> Path:
    p = tmp_path / filename
    if rows:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
        p.write_text(buf.getvalue(), encoding="utf-8")
    else:
        p.write_text("", encoding="utf-8")
    return p


def _gen(**kwargs) -> dcg.DatacardGenerator:
    defaults = dict(
        name="Test", description="desc", license="mit",
        source="", tags=[], version="0.1",
    )
    defaults.update(kwargs)
    return dcg.DatacardGenerator(**defaults)


# ── _safe_float ───────────────────────────────────────────────────────────── #

def test_safe_float_valid_float():
    assert dcg._safe_float("1.5") == 1.5

def test_safe_float_integer_string():
    assert dcg._safe_float("42") == 42.0

def test_safe_float_negative():
    assert dcg._safe_float("-3.14") == pytest.approx(-3.14)

def test_safe_float_invalid():
    assert dcg._safe_float("bad") is None

def test_safe_float_none():
    assert dcg._safe_float(None) is None

def test_safe_float_empty():
    assert dcg._safe_float("") is None


# ── _is_numeric ───────────────────────────────────────────────────────────── #

def test_is_numeric_floats():
    assert dcg._is_numeric(["1.0", "2.5", "3.14"])

def test_is_numeric_integers():
    assert dcg._is_numeric(["1", "2", "3"])

def test_is_numeric_strings():
    assert not dcg._is_numeric(["hello", "world"])

def test_is_numeric_empty_list():
    assert not dcg._is_numeric([])

def test_is_numeric_all_blank():
    assert not dcg._is_numeric(["", "  "])

def test_is_numeric_mixed_mostly_numeric():
    # 4 of 5 non-empty values parse → above the 80 % threshold
    assert dcg._is_numeric(["1", "2", "3", "4", "bad"])

def test_is_numeric_mixed_mostly_text():
    # 1 of 5 non-empty values parse → below the 80 % threshold
    assert not dcg._is_numeric(["a", "b", "c", "d", "1"])


# ── _field_stats ──────────────────────────────────────────────────────────── #

def test_field_stats_numeric_basics():
    s = dcg._field_stats(["1", "2", "3", "4", "5"])
    assert s["type"] == "numeric"
    assert s["min"] == 1.0
    assert s["max"] == 5.0
    assert s["mean"] == 3.0
    assert s["missing"] == 0
    assert s["count"] == 5

def test_field_stats_numeric_median_odd():
    s = dcg._field_stats(["1", "2", "3"])
    assert s["median"] == 2.0

def test_field_stats_numeric_median_even():
    s = dcg._field_stats(["1", "2", "3", "4"])
    assert s["median"] == 2.5

def test_field_stats_numeric_std():
    # Population std of [2,4,4,4,5,5,7,9] is 2.0
    s = dcg._field_stats(["2", "4", "4", "4", "5", "5", "7", "9"])
    assert s["type"] == "numeric"
    assert math.isclose(s["std"], 2.0, rel_tol=1e-4)

def test_field_stats_categorical():
    s = dcg._field_stats(["a", "b", "a", "c"])
    assert s["type"] == "categorical"
    assert s["unique"] == 3
    top = {tv["value"]: tv["count"] for tv in s["top_values"]}
    assert top["a"] == 2

def test_field_stats_missing_pct():
    s = dcg._field_stats(["1", "", "3"])
    assert s["missing"] == 1
    assert s["missing_pct"] == pytest.approx(100 / 3, abs=0.01)

def test_field_stats_top_values_limit():
    # More than 5 distinct categorical values — only top 5 should be returned.
    values = [f"cat_{i}" for i in range(10)]
    s = dcg._field_stats(values)
    assert s["type"] == "categorical"
    assert len(s["top_values"]) <= 5


# ── Import and public API surface ─────────────────────────────────────────── #

def test_import_datacardgenerator():
    assert hasattr(dcg, "DatacardGenerator")

def test_import_datacard():
    assert hasattr(dcg, "DataCard")

def test_import_fieldinfo():
    assert hasattr(dcg, "FieldInfo")


# ── DatacardGenerator.generate_from_dict ─────────────────────────────────── #

def test_generate_from_dict_numeric_column():
    card = _gen().generate_from_dict([{"x": "1"}, {"x": "2"}, {"x": "3"}])
    assert card.num_rows == 3
    assert card.num_cols == 1
    assert card.fields[0].dtype == "numeric"

def test_generate_from_dict_empty():
    card = _gen().generate_from_dict([])
    assert card.num_rows == 0
    assert card.num_cols == 0
    assert card.fields == []

def test_generate_from_dict_categorical():
    card = _gen().generate_from_dict(
        [{"color": "red"}, {"color": "blue"}, {"color": "red"}]
    )
    assert card.fields[0].dtype == "categorical"
    assert card.fields[0].stats["unique"] == 2

def test_generate_from_dict_mixed_columns():
    rows = [{"score": "0.9", "label": "pos"}, {"score": "0.1", "label": "neg"}]
    card = _gen().generate_from_dict(rows)
    dtypes = {f.name: f.dtype for f in card.fields}
    assert dtypes["score"] == "numeric"
    assert dtypes["label"] == "categorical"

def test_generate_from_dict_metadata_propagated():
    card = _gen(name="DS", version="2.0", license="cc0-1.0", tags=["nlp"]).generate_from_dict(
        [{"x": "1"}]
    )
    assert card.name == "DS"
    assert card.version == "2.0"
    assert card.license == "cc0-1.0"
    assert card.tags == ["nlp"]


# ── DatacardGenerator.generate_from_csv ──────────────────────────────────── #

def test_generate_from_csv_basic(tmp_path):
    p = _write_csv(tmp_path, [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}, {"a": 3, "b": "z"}])
    card = _gen().generate_from_csv(p)
    assert card.num_rows == 3
    assert card.num_cols == 2

def test_generate_from_csv_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        _gen().generate_from_csv(tmp_path / "missing.csv")

def test_generate_from_csv_stem_default(tmp_path):
    p = _write_csv(tmp_path, [{"x": "1"}], filename="mydata.csv")
    # The generator name is set at construction, not inferred from CSV;
    # test that the card carries the generator's name.
    card = dcg.DatacardGenerator(name="mydata").generate_from_csv(p)
    assert card.name == "mydata"


# ── DatacardGenerator.generate_from_string ───────────────────────────────── #

def test_generate_from_string_basic():
    csv_text = "a,b\n1,x\n2,y\n"
    card = _gen().generate_from_string(csv_text)
    assert card.num_rows == 2
    assert card.num_cols == 2

def test_generate_from_string_empty():
    card = _gen().generate_from_string("")
    assert card.num_rows == 0


# ── DatacardGenerator.generate (polymorphic) ──────────────────────────────── #

def test_generate_from_path(tmp_path):
    p = _write_csv(tmp_path, [{"v": "1"}, {"v": "2"}])
    card = _gen().generate(p)
    assert card.num_rows == 2

def test_generate_from_list():
    card = _gen().generate([{"a": 1}, {"a": 2}])
    assert card.num_rows == 2

def test_generate_from_column_dict():
    card = _gen().generate({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    assert card.num_rows == 3
    assert card.num_cols == 2

def test_generate_from_empty_dict():
    card = _gen().generate({})
    assert card.num_rows == 0

def test_generate_unsupported_type():
    with pytest.raises(TypeError, match="Unsupported source type"):
        _gen().generate(42)


# ── DataCard.to_json ──────────────────────────────────────────────────────── #

def test_to_json_is_valid_json():
    card = _gen(name="TestDS", tags=["nlp"]).generate_from_dict([{"score": "0.9"}])
    data = json.loads(card.to_json())
    assert data["name"] == "TestDS"
    assert data["num_rows"] == 1
    assert data["tags"] == ["nlp"]

def test_to_json_fields_present():
    card = _gen().generate_from_dict([{"a": "1", "b": "hello"}])
    data = json.loads(card.to_json())
    field_names = [f["name"] for f in data["fields"]]
    assert "a" in field_names and "b" in field_names

def test_to_dict_roundtrip():
    card = _gen().generate_from_dict([{"a": "1", "b": "hello"}])
    d = card.to_dict()
    assert d["num_rows"] == 1
    assert len(d["fields"]) == 2


# ── DataCard.to_markdown ──────────────────────────────────────────────────── #

def test_to_markdown_contains_name():
    card = _gen(name="MyDataset").generate_from_dict([{"x": "1"}])
    assert "# MyDataset" in card.to_markdown()

def test_to_markdown_frontmatter():
    card = _gen(name="DS", version="2.0.0", license="mit", tags=["cv"]).generate_from_dict(
        [{"x": "1"}]
    )
    md = card.to_markdown()
    assert md.startswith("---")
    assert "pretty_name: DS" in md
    assert "version: 2.0.0" in md
    assert "  - cv" in md

def test_to_markdown_table_separator_valid():
    """Regression: table separator must end with | not ]."""
    card = _gen().generate_from_dict([{"col": "1"}, {"col": "2"}])
    md = card.to_markdown()
    for line in md.splitlines():
        if line.startswith("|---"):
            assert line.endswith("|"), f"Malformed table separator: {line!r}"

def test_to_markdown_license_shown():
    card = _gen(license="cc0-1.0").generate_from_dict([{"x": "1"}])
    assert "cc0-1.0" in card.to_markdown()

def test_to_markdown_source_shown():
    card = _gen(source="https://example.com").generate_from_dict([{"x": "1"}])
    assert "https://example.com" in card.to_markdown()

def test_to_markdown_numeric_stats_shown():
    card = _gen().generate_from_dict([{"v": "1"}, {"v": "2"}, {"v": "3"}])
    md = card.to_markdown()
    assert "Min:" in md
    assert "Max:" in md
    assert "Mean:" in md

def test_to_markdown_categorical_top_values():
    card = _gen().generate_from_dict(
        [{"c": "a"}, {"c": "a"}, {"c": "b"}]
    )
    md = card.to_markdown()
    assert "Top values:" in md

def test_to_markdown_no_source_line():
    card = _gen(source="").generate_from_dict([{"x": "1"}])
    assert "Source:" not in card.to_markdown()


# ── CLI (main) ────────────────────────────────────────────────────────────── #

def test_main_returns_0_with_csv(tmp_path, capsys):
    p = _write_csv(tmp_path, [{"a": "1"}, {"a": "2"}])
    rc = dcg.main([str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# " in out  # markdown heading present

def test_main_json_format(tmp_path, capsys):
    p = _write_csv(tmp_path, [{"a": "1"}])
    rc = dcg.main([str(p), "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "num_rows" in data

def test_main_missing_file(capsys):
    rc = dcg.main(["nonexistent.csv"])
    assert rc == 1
    assert "not found" in capsys.readouterr().err

def test_main_output_file(tmp_path, capsys):
    p = _write_csv(tmp_path, [{"x": "1"}])
    out_file = tmp_path / "card.md"
    rc = dcg.main([str(p), "--output", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    assert "# " in out_file.read_text()

def test_main_tags_parsed(tmp_path, capsys):
    p = _write_csv(tmp_path, [{"x": "1"}])
    rc = dcg.main([str(p), "--tags", "nlp,cv", "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert "nlp" in data["tags"]
    assert "cv" in data["tags"]

def test_cli_alias_exists():
    assert dcg._cli is dcg.main
