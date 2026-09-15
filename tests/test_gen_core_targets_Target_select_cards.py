import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_select_cards_normal_input():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', 
                    context_before='', context_after='', missing='', executed_in_body=False, complexity=0, 
                    io_deps=[], is_async=False, is_property=False, module_imports=[], 
                    io_kinds=["time"], is_method=True, raises_in_missing=False, calls_imported=True)
    result = target.select_cards("characterize", 2)
    assert result == ['characterize', 'time-and-random', 'class-and-state']

def test_characterize_select_cards_empty_input():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', 
                    context_before='', context_after='', missing='', executed_in_body=False, complexity=0, 
                    io_deps=[], is_async=False, is_property=False, module_imports=[], 
                    io_kinds=[], is_method=False, raises_in_missing=False, calls_imported=False)
    result = target.select_cards("characterize", 2)
    assert result == ['characterize', 'pure-function']

def test_characterize_select_cards_with_exception_paths():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', 
                    context_before='', context_after='', missing='', executed_in_body=False, complexity=0, 
                    io_deps=[], is_async=False, is_property=False, module_imports=[], 
                    io_kinds=["filesystem"], is_method=False, raises_in_missing=True, calls_imported=False)
    result = target.select_cards("characterize", 2)
    assert result == ['characterize', 'filesystem', 'exception-paths']

def test_characterize_select_cards_with_patch():
    target = Target(file='', module='', name='', qualname='', class_name='', lineno=0, end=0, body_lo='', src='', 
                    context_before='', context_after='', missing='', executed_in_body=False, complexity=0, 
                    io_deps=[], is_async=False, is_property=False, module_imports=[], 
                    io_kinds=["network"], is_method=True, raises_in_missing=False, calls_imported=True)
    result = target.select_cards("characterize", 2)
    assert result == ['characterize', 'filesystem', 'class-and-state']