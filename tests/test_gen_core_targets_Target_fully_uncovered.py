import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_fully_uncovered_normal_case():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', missing='', executed_in_body=0, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.fully_uncovered
    assert result == True

def test_characterize_fully_uncovered_non_zero_executed():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', missing='', executed_in_body=1, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.fully_uncovered
    assert result == False

def test_characterize_fully_uncovered_empty_case():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', missing='', executed_in_body=0, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.fully_uncovered
    assert result == True

def test_characterize_fully_uncovered_boundary_case():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', missing='', executed_in_body=-1, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.fully_uncovered
    assert result == False