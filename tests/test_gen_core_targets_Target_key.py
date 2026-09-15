import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_target_key_normal_input():
    target = Target(module="example_module", name="ExampleClass", class_name="ExampleClass", lineno=1, end=1, body_lo=1, src="", context_before="", context_after="", missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], file="example.py", qualname="ExampleClass")
    result = target.key
    assert result == "example.py::ExampleClass"

def test_characterize_target_key_empty_file():
    target = Target(module="example_module", name="ExampleClass", class_name="ExampleClass", lineno=1, end=1, body_lo=1, src="", context_before="", context_after="", missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], file="", qualname="ExampleClass")
    result = target.key
    assert result == "::ExampleClass"

def test_characterize_target_key_empty_qualname():
    target = Target(module="example_module", name="ExampleClass", class_name="ExampleClass", lineno=1, end=1, body_lo=1, src="", context_before="", context_after="", missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], file="example.py", qualname="")
    result = target.key
    assert result == "example.py::"

def test_characterize_target_key_both_empty():
    target = Target(module="example_module", name="ExampleClass", class_name="ExampleClass", lineno=1, end=1, body_lo=1, src="", context_before="", context_after="", missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], file="", qualname="")
    result = target.key
    assert result == "::"