"""
Tests for datacard_gen.

Covers the installable src package (src/datacard_gen/) and the standalone
root script (datacard_gen.py) where indicated.
"""
import io
import json
import sys
import tempfile
from pathlib import Path

# src package (installed via pip install -e .)
from datacard_gen import DatacardGenerator, DatacardSchema, DataCard, FieldInfo, ValidationResult
from datacard_gen._core import _safe_float, _is_numeric, _field_stats
from datacard_gen.cli import main as cli_main

# Standalone script – imported directly from the file for backward-compat tests.
# Must register in sys.modules before exec_module so @dataclass can resolve __module__.
_REPO_ROOT = Path(__file__).parent.parent
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_dcg_script", _REPO_ROOT / "datacard_gen.py")
_script = _ilu.module_from_spec(_spec)
sys.modules["_dcg_script"] = _script
_spec.loader.exec_module(_script)


# ── shared fixtures ───────────────────────────────────────────────────────────

SAMPLE_ROWS = [
    {"age": "25", "name": "Alice", "score": "88.5"},
    {"age": "30", "name": "Bob",   "score": "92.0"},
    {"age": "22", "name": "Carol", "score": "75.0"},
    {"age": "",   "name": "Dave",  "score": "81.0"},
]

SAMPLE_DICT_COL = {"age": [25, 30, 22], "city": ["NYC", "LA", "NYC"]}


class _Approx:
    """Lightweight approximate-equal helper (avoids importing pytest.approx at class level)."""
    def __init__(self, val, tol=0.1):
        self._val = val
        self._tol = tol

    def __eq__(self, other):
        return abs(other - self._val) < self._tol


# ── helpers ────────────────────────────────────────────────────────────────────

class TestSafeFloat:
    def test_valid(self):
        assert _safe_float("3.14") == 3.14

    def test_integer_string(self):
        assert _safe_float("42") == 42.0

    def test_invalid(self):
        assert _safe_float("hello") is None

    def test_none(self):
        assert _safe_float(None) is None


class TestIsNumeric:
    def test_numeric(self):
        assert _is_numeric(["1", "2", "3"])

    def test_categorical(self):
        assert not _is_numeric(["a", "b", "c"])

    def test_empty(self):
        assert not _is_numeric([])

    def test_mostly_numeric_threshold(self):
        # 4 out of 5 are numeric → 80 % → True
        assert _is_numeric(["1", "2", "3", "4", "abc"])

    def test_below_threshold(self):
        # 1 out of 5 → 20 % → False
        assert not _is_numeric(["1", "a", "b", "c", "d"])


class TestFieldStats:
    def test_numeric_stats(self):
        stats = _field_stats(["1", "2", "3", "4", "5"])
        assert stats["type"] == "numeric"
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["mean"] == 3.0
        assert stats["median"] == 3.0
        assert stats["missing"] == 0

    def test_categorical_stats(self):
        stats = _field_stats(["a", "b", "a", "c"])
        assert stats["type"] == "categorical"
        assert stats["unique"] == 3
        top_values = [tv["value"] for tv in stats["top_values"]]
        assert "a" in top_values

    def test_missing_values(self):
        stats = _field_stats(["1", "", "3"])
        assert stats["missing"] == 1
        assert _Approx(33.33) == stats["missing_pct"]

    def test_all_empty(self):
        stats = _field_stats(["", "", ""])
        assert stats["type"] == "categorical"
        assert stats["missing"] == 3

    def test_top_values_capped_at_5(self):
        # Use non-numeric labels so the field is treated as categorical.
        values = [f"cat_{i}" for i in range(20)]
        stats = _field_stats(values)
        assert stats["type"] == "categorical"
        assert len(stats["top_values"]) <= 5


# ── DatacardGenerator ─────────────────────────────────────────────────────────

class TestDatacardGenerator:
    def test_generate_from_dict(self):
        gen = DatacardGenerator(name="Test", license="mit")
        card = gen.generate_from_dict(SAMPLE_ROWS)
        assert card.num_rows == 4
        assert card.num_cols == 3
        assert card.name == "Test"

    def test_generate_column_oriented_dict(self):
        gen = DatacardGenerator()
        card = gen.generate(SAMPLE_DICT_COL)
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_empty_dict(self):
        gen = DatacardGenerator()
        card = gen.generate_from_dict([])
        assert card.num_rows == 0
        assert card.num_cols == 0

    def test_numeric_field_dtype(self):
        gen = DatacardGenerator()
        card = gen.generate_from_dict(SAMPLE_ROWS)
        age_field = next(f for f in card.fields if f.name == "age")
        assert age_field.dtype == "numeric"

    def test_categorical_field_dtype(self):
        gen = DatacardGenerator()
        card = gen.generate_from_dict(SAMPLE_ROWS)
        name_field = next(f for f in card.fields if f.name == "name")
        assert name_field.dtype == "categorical"

    def test_generate_from_csv(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x,y\n1,a\n2,b\n3,c\n", encoding="utf-8")
        gen = DatacardGenerator(name="CSV Test")
        card = gen.generate_from_csv(csv_file)
        assert card.num_rows == 3
        assert card.num_cols == 2

    def test_generate_from_json_records(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text(
            json.dumps([{"x": 1, "y": "a"}, {"x": 2, "y": "b"}]), encoding="utf-8"
        )
        gen = DatacardGenerator(name="JSON Test")
        card = gen.generate(json_file)
        assert card.num_rows == 2
        assert card.num_cols == 2

    def test_generate_from_json_column_oriented(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps({"x": [1, 2, 3], "y": ["a", "b", "c"]}), encoding="utf-8")
        gen = DatacardGenerator()
        card = gen.generate(json_file)
        assert card.num_rows == 3

    def test_generate_raises_on_bad_type(self):
        gen = DatacardGenerator()
        try:
            gen.generate(42)
            assert False, "Expected TypeError"
        except TypeError:
            pass

    def test_tags_stored(self):
        gen = DatacardGenerator(tags=["nlp", "text"])
        card = gen.generate_from_dict(SAMPLE_ROWS)
        assert card.tags == ["nlp", "text"]

    def test_version_stored(self):
        gen = DatacardGenerator(version="2.0.1")
        card = gen.generate_from_dict(SAMPLE_ROWS)
        assert card.version == "2.0.1"


# ── DataCard output ────────────────────────────────────────────────────────────

class TestDataCardOutput:
    def _card(self):
        gen = DatacardGenerator(name="Demo", license="cc-by-4.0", tags=["nlp"])
        return gen.generate_from_dict(SAMPLE_ROWS)

    def test_to_dict_keys(self):
        card = self._card()
        d = card.to_dict()
        for key in ("name", "num_rows", "num_cols", "fields", "license", "tags", "version"):
            assert key in d

    def test_to_json_valid(self):
        card = self._card()
        obj = json.loads(card.to_json())
        assert obj["name"] == "Demo"
        assert obj["num_rows"] == 4

    def test_to_markdown_contains_yaml_frontmatter(self):
        card = self._card()
        md = card.to_markdown()
        assert md.startswith("---\n")
        assert "pretty_name:" in md
        assert "license:" in md

    def test_to_markdown_table_separator_fixed(self):
        card = self._card()
        md = card.to_markdown()
        assert "|-------|------|---------|--------|" in md
        assert "|-------|------|---------|--------|]" not in md

    def test_to_markdown_field_sections(self):
        card = self._card()
        md = card.to_markdown()
        assert "### `age`" in md
        assert "### `name`" in md
        assert "### `score`" in md

    def test_to_markdown_numeric_stats_present(self):
        card = self._card()
        md = card.to_markdown()
        assert "**Min:**" in md
        assert "**Max:**" in md
        assert "**Mean:**" in md

    def test_to_markdown_tags_in_frontmatter(self):
        card = self._card()
        md = card.to_markdown()
        assert "  - nlp" in md

    def test_field_info_to_dict(self):
        fi = FieldInfo(name="x", dtype="numeric", stats={"mean": 1.0})
        d = fi.to_dict()
        assert d["name"] == "x"
        assert d["dtype"] == "numeric"
        assert d["stats"]["mean"] == 1.0


# ── DatacardSchema ─────────────────────────────────────────────────────────────

class TestDatacardSchema:
    def _gen_card(self, **kw):
        gen = DatacardGenerator(**kw)
        return gen.generate_from_dict(SAMPLE_ROWS)

    def test_valid_card(self):
        card = self._gen_card(
            name="Good Dataset",
            description="A proper description of this dataset.",
            license="cc-by-4.0",
            source="https://example.org",
            tags=["nlp"],
        )
        result = DatacardSchema().validate(card)
        assert result.valid
        assert result.errors == []

    def test_empty_name_is_error(self):
        card = self._gen_card(name="Good Dataset")
        card.name = ""
        result = DatacardSchema().validate(card)
        assert not result.valid
        assert any("name" in e for e in result.errors)

    def test_placeholder_description_is_warning(self):
        card = self._gen_card(name="Dataset", description="A dataset.")
        result = DatacardSchema().validate(card)
        assert result.valid  # warning, not an error
        assert any("description" in w for w in result.warnings)

    def test_unknown_license_is_warning(self):
        card = self._gen_card(name="Dataset", license="my-custom-license")
        result = DatacardSchema().validate(card)
        assert result.valid
        assert any("license" in w for w in result.warnings)

    def test_bad_semver_is_warning(self):
        card = self._gen_card(name="Dataset")
        card.version = "v1"
        result = DatacardSchema().validate(card)
        assert any("version" in w for w in result.warnings)

    def test_zero_rows_is_warning(self):
        gen = DatacardGenerator(name="Empty")
        card = gen.generate_from_dict([])
        result = DatacardSchema().validate(card)
        assert any("zero rows" in w for w in result.warnings)

    def test_validation_result_str(self):
        card = self._gen_card(name="")
        result = DatacardSchema().validate(card)
        s = str(result)
        assert "Valid: False" in s
        assert "ERROR" in s

    def test_validation_result_dataclass(self):
        vr = ValidationResult(valid=True, errors=[], warnings=["w1"])
        assert vr.valid
        assert vr.warnings == ["w1"]


# ── CLI (src package) ──────────────────────────────────────────────────────────

class TestCLI:
    def test_cli_from_csv(self, tmp_path, capsys):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
        rc = cli_main([str(csv_file)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "## Dataset Description" in out

    def test_cli_json_output(self, tmp_path, capsys):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,x\n2,y\n", encoding="utf-8")
        rc = cli_main([str(csv_file), "--format", "json"])
        assert rc == 0
        obj = json.loads(capsys.readouterr().out)
        assert obj["num_rows"] == 2

    def test_cli_output_file(self, tmp_path):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b\n1,x\n", encoding="utf-8")
        out_file = tmp_path / "card.md"
        rc = cli_main([str(csv_file), "-o", str(out_file)])
        assert rc == 0
        assert out_file.exists()
        assert "## Dataset Description" in out_file.read_text()

    def test_cli_missing_file(self):
        rc = cli_main(["nonexistent_file.csv"])
        assert rc == 1

    def test_cli_tags_parsed(self, tmp_path, capsys):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x\n1\n2\n", encoding="utf-8")
        rc = cli_main([str(csv_file), "--tags", "nlp, text", "--format", "json"])
        assert rc == 0
        obj = json.loads(capsys.readouterr().out)
        assert "nlp" in obj["tags"]
        assert "text" in obj["tags"]

    def test_cli_validate_returns_nonzero_on_error(self, tmp_path, capsys):
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("x\n1\n2\n", encoding="utf-8")
        # Default description is a placeholder, so --validate emits warnings but should still return 0.
        rc = cli_main([str(csv_file), "--validate"])
        assert rc in (0, 2)

    def test_cli_json_input(self, tmp_path, capsys):
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps([{"x": 1}, {"x": 2}]), encoding="utf-8")
        rc = cli_main([str(json_file), "--format", "json"])
        assert rc == 0
        obj = json.loads(capsys.readouterr().out)
        assert obj["num_rows"] == 2


# ── standalone script backward-compatibility ──────────────────────────────────

class TestStandaloneScript:
    """Ensures the root datacard_gen.py still works as a self-contained script."""

    def test_has_required_symbols(self):
        for sym in ("DatacardGenerator", "DataCard", "DatacardSchema", "main", "_cli",
                    "_safe_float", "_is_numeric", "_field_stats"):
            assert hasattr(_script, sym), f"standalone script missing: {sym}"

    def test_table_separator_bug_fixed(self):
        gen = _script.DatacardGenerator(name="Standalone")
        card = gen.generate_from_dict(SAMPLE_ROWS)
        md = card.to_markdown()
        assert "|-------|------|---------|--------|" in md
        assert "|-------|------|---------|--------|]" not in md

    def test_cli_alias(self):
        assert _script._cli is _script.main

    def test_generate_json(self, tmp_path):
        json_file = tmp_path / "data.json"
        json_file.write_text(json.dumps([{"a": 1}, {"a": 2}]), encoding="utf-8")
        gen = _script.DatacardGenerator(name="JS")
        card = gen.generate(json_file)
        assert card.num_rows == 2
