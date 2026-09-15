import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_import_lines_with_class_name():
    target = Target(file="test_file.py", qualname="MyClass", lineno=1, end=2, body_lo=0, src="", context_before=[], context_after=[], missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], module="core.module", name="MyClass", class_name="MyClass")
    result = target.import_lines
    assert result == ['from core.module import MyClass', 'import core.module as module']

def test_characterize_import_lines_without_class_name():
    target = Target(file="test_file.py", qualname="MyModule", lineno=1, end=2, body_lo=0, src="", context_before=[], context_after=[], missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], module="core.module", name="MyModule", class_name=None)
    result = target.import_lines
    assert result == ['from core.module import MyModule', 'import core.module as module']

def test_characterize_import_lines_with_same_name_as_module():
    target = Target(file="test_file.py", qualname="module", lineno=1, end=2, body_lo=0, src="", context_before=[], context_after=[], missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[], module="core.module", name="module", class_name=None)
    result = target.import_lines
    assert result == ['from core.module import module', 'import core.module as module_mod']
