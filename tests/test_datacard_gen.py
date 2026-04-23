import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

def test_import():
    import datacard_gen as dcg
    assert hasattr(dcg, 'DatacardGenerator')

def test_is_numeric_true():
    import datacard_gen as dcg
    assert dcg._is_numeric('3.14')

def test_is_numeric_false():
    import datacard_gen as dcg
    assert not dcg._is_numeric('hello')

def test_safe_float():
    import datacard_gen as dcg
    assert dcg._safe_float('1.5') == 1.5
    assert dcg._safe_float('bad') is None
