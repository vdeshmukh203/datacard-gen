"""
Tests for datacard_gen — JOSS review quality.

Covers: helper functions, DataCard model, DatacardGenerator API (dict, CSV,
JSON inputs), CLI argument parsing, and Markdown / JSON output correctness.
"""

import csv
import io
import json
import math
import pathlib
import sys
import tempfile

import pytest

# Make the top-level module importable when running from the repo root.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import datacard_gen as dcg


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_integer_string(self):
        assert dcg._safe_float("42") == 42.0

    def test_float_string(self):
        assert dcg._safe_float("3.14") == pytest.approx(3.14)

    def test_negative(self):
        assert dcg._safe_float("-7.5") == pytest.approx(-7.5)

    def test_non_numeric_string(self):
        assert dcg._safe_float("hello") is None

    def test_none_input(self):
        assert dcg._safe_float(None) is None

    def test_numeric_type_passthrough(self):
        assert dcg._safe_float(2.0) == 2.0


# ---------------------------------------------------------------------------
# _is_numeric
# ---------------------------------------------------------------------------

class TestIsNumeric:
    def test_all_numeric(self):
        assert dcg._is_numeric(["1", "2.5", "3"])

    def test_all_text(self):
        assert not dcg._is_numeric(["cat", "dog"])

    def test_empty_list(self):
        assert not dcg._is_numeric([])

    def test_all_blank(self):
        assert not dcg._is_numeric(["", "  "])

    def test_mixed_below_threshold(self):
        # Only 1 of 5 numeric → below 0.8 threshold → categorical
        assert not dcg._is_numeric(["1", "a", "b", "c", "d"])

    def test_mixed_above_threshold(self):
        # 4 of 5 numeric → above 0.8 threshold → numeric
        assert dcg._is_numeric(["1", "2", "3", "4", "x"])


# ---------------------------------------------------------------------------
# _field_stats
# ---------------------------------------------------------------------------

class TestFieldStats:
    def test_numeric_stats_keys(self):
        stats = dcg._field_stats(["1", "2", "3", "4", "5"])
        for key in ("min", "max", "mean", "std", "median", "count", "missing", "unique"):
            assert key in stats

    def test_numeric_mean(self):
        stats = dcg._field_stats(["1", "2", "3", "4", "5"])
        assert stats["mean"] == pytest.approx(3.0)

    def test_numeric_std(self):
        # Population std of [1,2,3,4,5] = sqrt(2)
        stats = dcg._field_stats(["1", "2", "3", "4", "5"])
        assert stats["std"] == pytest.approx(math.sqrt(2), abs=1e-3)

    def test_numeric_median_odd(self):
        stats = dcg._field_stats(["1", "2", "3"])
        assert stats["median"] == 2.0

    def test_numeric_median_even(self):
        stats = dcg._field_stats(["1", "2", "3", "4"])
        assert stats["median"] == 2.5

    def test_missing_count(self):
        stats = dcg._field_stats(["1", "", "3"])
        assert stats["missing"] == 1
        assert stats["missing_pct"] == pytest.approx(100 / 3, abs=0.1)

    def test_categorical_top_values(self):
        stats = dcg._field_stats(["a", "a", "b", "b", "b", "c"])
        top = {entry["value"]: entry["count"] for entry in stats["top_values"]}
        assert top["b"] == 3
        assert top["a"] == 2

    def test_categorical_unique_count(self):
        stats = dcg._field_stats(["x", "y", "x", "z"])
        assert stats["unique"] == 3

    def test_type_not_in_returned_stats(self):
        # _build_card pops "type" out; _field_stats itself keeps it
        stats = dcg._field_stats(["1", "2"])
        assert "type" in stats


# ---------------------------------------------------------------------------
# DataCard model
# ---------------------------------------------------------------------------

class TestDataCard:
    def _make_card(self) -> dcg.DataCard:
        fi = dcg.FieldInfo(
            name="score",
            dtype="numeric",
            stats={"count": 3, "missing": 0, "missing_pct": 0.0, "unique": 3,
                   "min": 1.0, "max": 3.0, "mean": 2.0, "std": 0.816, "median": 2.0},
        )
        return dcg.DataCard(
            name="TestDS", description="A test dataset.",
            num_rows=3, num_cols=1, fields=[fi],
            license="cc-by-4.0", tags=["test"],
        )

    def test_to_dict_keys(self):
        card = self._make_card()
        d = card.to_dict()
        for key in ("name", "description", "num_rows", "num_cols", "license", "fields", "tags"):
            assert key in d

    def test_to_json_is_valid(self):
        card = self._make_card()
        parsed = json.loads(card.to_json())
        assert parsed["name"] == "TestDS"
        assert parsed["num_rows"] == 3

    def test_to_markdown_contains_name(self):
        md = self._make_card().to_markdown()
        assert "# TestDS" in md

    def test_to_markdown_table_valid(self):
        md = self._make_card().to_markdown()
        # The separator line must NOT contain a stray ']'
        for line in md.splitlines():
            if line.startswith("|---"):
                assert "]" not in line

    def test_to_markdown_frontmatter(self):
        md = self._make_card().to_markdown()
        assert md.startswith("---\n")
        assert "license: cc-by-4.0" in md

    def test_to_markdown_tags(self):
        md = self._make_card().to_markdown()
        assert "  - test" in md

    def test_to_markdown_numeric_fields(self):
        md = self._make_card().to_markdown()
        assert "**Min:**" in md
        assert "**Max:**" in md
        assert "**Mean:**" in md

    def test_to_markdown_source_omitted_when_empty(self):
        card = self._make_card()
        card.source = ""
        md = card.to_markdown()
        assert "**Source:**" not in md

    def test_to_markdown_source_present(self):
        card = self._make_card()
        card.source = "https://example.com/data"
        md = card.to_markdown()
        assert "https://example.com/data" in md


# ---------------------------------------------------------------------------
# DatacardGenerator — dict / list input
# ---------------------------------------------------------------------------

class TestGeneratorFromDict:
    def _gen(self, **kwargs) -> dcg.DatacardGenerator:
        return dcg.DatacardGenerator(name="DS", description="desc.", **kwargs)

    def test_basic_list_of_dicts(self):
        rows = [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}]
        card = self._gen().generate_from_dict(rows)
        assert card.num_rows == 2
        assert card.num_cols == 2

    def test_columnar_dict_via_generate(self):
        data = {"x": [1, 2, 3], "y": ["a", "b", "c"]}
        card = self._gen().generate(data)
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_empty_input(self):
        card = self._gen().generate_from_dict([])
        assert card.num_rows == 0
        assert card.num_cols == 0

    def test_tags_propagated(self):
        card = dcg.DatacardGenerator(name="DS", description="d.", tags=["ml", "nlp"]).generate_from_dict(
            [{"v": "1"}]
        )
        assert "ml" in card.tags

    def test_license_propagated(self):
        card = dcg.DatacardGenerator(name="DS", description="d.", license="mit").generate_from_dict(
            [{"v": "1"}]
        )
        assert card.license == "mit"

    def test_unsupported_type_raises(self):
        gen = self._gen()
        with pytest.raises(TypeError):
            gen.generate("not-a-path-or-list")


# ---------------------------------------------------------------------------
# DatacardGenerator — CSV file input
# ---------------------------------------------------------------------------

class TestGeneratorFromCSV:
    def _write_csv(self, tmp_path: pathlib.Path, rows) -> pathlib.Path:
        p = tmp_path / "data.csv"
        with p.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return p

    def test_csv_row_count(self, tmp_path):
        rows = [{"a": str(i), "b": "x"} for i in range(10)]
        p = self._write_csv(tmp_path, rows)
        card = dcg.DatacardGenerator(name="DS", description="d.").generate_from_csv(p)
        assert card.num_rows == 10

    def test_csv_column_count(self, tmp_path):
        rows = [{"col1": "1", "col2": "2", "col3": "3"}]
        p = self._write_csv(tmp_path, rows)
        card = dcg.DatacardGenerator(name="DS", description="d.").generate_from_csv(p)
        assert card.num_cols == 3

    def test_csv_numeric_column_detected(self, tmp_path):
        rows = [{"val": str(i)} for i in range(5)]
        p = self._write_csv(tmp_path, rows)
        card = dcg.DatacardGenerator(name="DS", description="d.").generate_from_csv(p)
        assert card.fields[0].dtype == "numeric"

    def test_csv_categorical_column_detected(self, tmp_path):
        rows = [{"label": lbl} for lbl in ["cat", "dog", "fish"]]
        p = self._write_csv(tmp_path, rows)
        card = dcg.DatacardGenerator(name="DS", description="d.").generate_from_csv(p)
        assert card.fields[0].dtype == "categorical"

    def test_generate_dispatches_csv_by_extension(self, tmp_path):
        rows = [{"n": "1"}]
        p = self._write_csv(tmp_path, rows)
        card = dcg.DatacardGenerator(name="DS", description="d.").generate(p)
        assert card.num_rows == 1


# ---------------------------------------------------------------------------
# DatacardGenerator — JSON file input
# ---------------------------------------------------------------------------

class TestGeneratorFromJSON:
    def test_json_list_of_records(self, tmp_path):
        data = [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}]
        p = tmp_path / "data.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        card = dcg.DatacardGenerator(name="DS", description="d.").generate_from_json(p)
        assert card.num_rows == 2
        assert card.num_cols == 2

    def test_json_columnar_dict(self, tmp_path):
        data = {"a": [1, 2, 3], "b": ["x", "y", "z"]}
        p = tmp_path / "data.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        card = dcg.DatacardGenerator(name="DS", description="d.").generate_from_json(p)
        assert card.num_rows == 3

    def test_json_dispatched_by_extension(self, tmp_path):
        data = [{"v": "1"}]
        p = tmp_path / "data.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        card = dcg.DatacardGenerator(name="DS", description="d.").generate(p)
        assert card.num_rows == 1

    def test_json_invalid_structure_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text('"just a string"', encoding="utf-8")
        with pytest.raises(ValueError):
            dcg.DatacardGenerator(name="DS", description="d.").generate_from_json(p)


# ---------------------------------------------------------------------------
# CLI — argument parsing and end-to-end
# ---------------------------------------------------------------------------

class TestCLI:
    def _run(self, argv):
        return dcg.main(argv)

    def test_missing_file_returns_1(self):
        assert self._run(["nonexistent.csv"]) == 1

    def test_csv_to_stdout_returns_0(self, tmp_path, capsys):
        rows = [{"a": "1", "b": "hello"}]
        p = tmp_path / "d.csv"
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["a", "b"])
            w.writeheader()
            w.writerows(rows)
        rc = self._run([str(p)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "# d" in out  # name defaults to file stem

    def test_json_output_format(self, tmp_path, capsys):
        rows = [{"a": "1"}]
        p = tmp_path / "d.csv"
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["a"])
            w.writeheader()
            w.writerows(rows)
        rc = self._run([str(p), "--format", "json"])
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert "fields" in parsed

    def test_output_file_written(self, tmp_path):
        rows = [{"v": "1"}]
        p = tmp_path / "d.csv"
        out_p = tmp_path / "card.md"
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["v"])
            w.writeheader()
            w.writerows(rows)
        rc = self._run([str(p), "--output", str(out_p)])
        assert rc == 0
        assert out_p.exists()
        assert len(out_p.read_text()) > 0

    def test_custom_name_and_license(self, tmp_path, capsys):
        rows = [{"v": "1"}]
        p = tmp_path / "d.csv"
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["v"])
            w.writeheader()
            w.writerows(rows)
        rc = self._run([str(p), "--name", "MyCustomDS", "--license", "mit"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "MyCustomDS" in out
        assert "mit" in out

    def test_tags_appear_in_output(self, tmp_path, capsys):
        rows = [{"v": "1"}]
        p = tmp_path / "d.csv"
        with p.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["v"])
            w.writeheader()
            w.writerows(rows)
        self._run([str(p), "--tags", "nlp,vision"])
        out = capsys.readouterr().out
        assert "nlp" in out
        assert "vision" in out

    def test_stdin_csv(self, monkeypatch, capsys):
        csv_data = "col\n1\n2\n3\n"
        monkeypatch.setattr("sys.stdin", io.StringIO(csv_data))
        rc = self._run([])
        assert rc == 0
        out = capsys.readouterr().out
        assert "dataset" in out.lower()


# ---------------------------------------------------------------------------
# DatacardSchema (src package)
# ---------------------------------------------------------------------------

class TestDatacardSchema:
    def test_import(self):
        from src.datacard_gen.schema import DatacardSchema
        assert DatacardSchema is not None

    def test_valid_schema(self):
        from src.datacard_gen.schema import DatacardSchema
        schema = DatacardSchema(name="DS", description="A dataset.")
        assert schema.is_valid()

    def test_empty_name_invalid(self):
        from src.datacard_gen.schema import DatacardSchema
        schema = DatacardSchema(name="", description="desc")
        issues = schema.validate()
        assert any("name" in i for i in issues)

    def test_empty_description_invalid(self):
        from src.datacard_gen.schema import DatacardSchema
        schema = DatacardSchema(name="DS", description="")
        issues = schema.validate()
        assert any("description" in i for i in issues)

    def test_unknown_license_flagged(self):
        from src.datacard_gen.schema import DatacardSchema
        schema = DatacardSchema(name="DS", description="d.", license="unknown")
        issues = schema.validate()
        assert any("license" in i for i in issues)

    def test_field_schema_invalid_dtype(self):
        from src.datacard_gen.schema import DatacardSchema, FieldSchema
        schema = DatacardSchema(
            name="DS", description="d.",
            fields=[FieldSchema(name="col", dtype="bogus")]
        )
        issues = schema.validate()
        assert any("dtype" in i for i in issues)
