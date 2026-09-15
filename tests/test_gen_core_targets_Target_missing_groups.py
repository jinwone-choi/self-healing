import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_target_missing_groups_normal_input():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], missing=[1, 2, 3, 5, 6, 8])
    result = target.missing_groups
    assert result == [(1, 3), (5, 6), (8, 8)]

def test_characterize_target_missing_groups_empty_input():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], missing=[])
    result = target.missing_groups
    assert result == []

def test_characterize_target_missing_groups_single_group():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], missing=[1, 2, 3])
    result = target.missing_groups
    assert result == [(1, 3)]

def test_characterize_target_missing_groups_non_consecutive():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo=0, src='', context_before='', context_after='', executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], missing=[1, 3, 4, 6, 7, 9])
    result = target.missing_groups
    assert result == [(1, 1), (3, 4), (6, 7), (9, 9)]