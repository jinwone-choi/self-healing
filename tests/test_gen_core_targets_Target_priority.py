import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_target_priority_normal():
    target = Target(file='test.py', module='test', name='test_characterize_target_priority_normal', qualname='test_characterize_target_priority_normal', class_name=None, lineno=1, end=2, body_lo=3, src='', context_before='', context_after='', executed_in_body=False, io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], missing=[1, 2], complexity=4, io_deps=[3])
    result = target.priority
    assert result == 0.3333333333333333

def test_characterize_target_priority_empty():
    target = Target(file='test.py', module='test', name='test_characterize_target_priority_empty', qualname='test_characterize_target_priority_empty', class_name=None, lineno=1, end=2, body_lo=3, src='', context_before='', context_after='', executed_in_body=False, io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], missing=[], complexity=0, io_deps=[])
    result = target.priority
    assert result == 0.0

def test_characterize_target_priority_boundary():
    target = Target(file='test.py', module='test', name='test_characterize_target_priority_boundary', qualname='test_characterize_target_priority_boundary', class_name=None, lineno=1, end=2, body_lo=3, src='', context_before='', context_after='', executed_in_body=False, io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], missing=[1], complexity=2, io_deps=[3, 4, 5])
    result = target.priority
    assert result == 0.09090909090909091