import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_target_is_pure_no_io_deps_and_not_async():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', context_before='', context_after='', missing='', executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.is_pure
    assert result == True

def test_characterize_target_is_pure_with_io_deps():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', context_before='', context_after='', missing='', executed_in_body=False, complexity=0, io_deps=['file.txt'], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.is_pure
    assert result == False

def test_characterize_target_is_pure_with_async():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', context_before='', context_after='', missing='', executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=True, is_property=False, module_imports=[])
    result = target.is_pure
    assert result == False

def test_characterize_target_is_pure_empty_io_deps_and_async():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', context_before='', context_after='', missing='', executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.is_pure
    assert result == True