import pytest
from core.prompt import _gap_block
import core.prompt as prompt

class MockTarget:
    def __init__(self, missing, fully_uncovered=False, missing_groups=None):
        self.missing = missing
        self.fully_uncovered = fully_uncovered
        self.missing_groups = missing_groups or []

def test_characterize_gap_block_fully_uncovered():
    target = MockTarget(missing=[], fully_uncovered=True)
    result = _gap_block(target)
    assert result == 'This function has never been executed by any test. Write tests that call it.\n'

def test_characterize_gap_block_partially_covered():
    target = MockTarget(missing=["func_a", "func_b"], fully_uncovered=False, missing_groups=[("func_a", "func_b")])
    result = _gap_block(target)
    assert result == 'This function is partially covered. The lines marked with >> (lines func_a-func_b) have NOT been executed yet. Choose inputs that make execution reach those lines.\n'

def test_characterize_gap_block_empty_missing():
    target = MockTarget(missing=[], fully_uncovered=False)
    result = _gap_block(target)
    assert result == 'This function is partially covered. The lines marked with >> (lines ) have NOT been executed yet. Choose inputs that make execution reach those lines.\n'

def test_characterize_gap_block_with_groups():
    target = MockTarget(missing=["func_a", "func_b"], fully_uncovered=False, missing_groups=[("func_a", "func_a"), ("func_b", "func_b")])
    result = _gap_block(target)
    assert result == 'This function is partially covered. The lines marked with >> (lines func_a, func_b) have NOT been executed yet. Choose inputs that make execution reach those lines.\n'