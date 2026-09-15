import pytest
from core.targets import Target
import core.targets as targets

def test_characterize_module_alias_normal_input():
    target = Target(module="core.module", name="module", file="", qualname="", class_name="", lineno=0, end=0, body_lo=0, src="", context_before="", context_after="", missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.module_alias
    assert result == "module_mod"


def test_characterize_module_alias_empty_input():
    target = Target(module="", name="", file="", qualname="", class_name="", lineno=0, end=0, body_lo=0, src="", context_before="", context_after="", missing=[], executed_in_body=False, complexity=0, io_deps=[], io_kinds=[], calls_imported=[], raises_in_missing=[], is_method=False, is_async=False, is_property=False, module_imports=[])
    result = target.module_alias
    assert result == "_mod"
