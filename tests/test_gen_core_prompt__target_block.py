import pytest
from core.prompt import _target_block
import core.prompt as prompt

class MockTarget:
    def __init__(self, file, module, class_name=None, name=None, import_lines=None, calls_imported=False, io_deps=False):
        self.file = file
        self.module = module
        self.class_name = class_name
        self.name = name
        self.import_lines = import_lines or []
        self.calls_imported = calls_imported
        self.io_deps = io_deps

def test_characterize_target_block_normal_input():
    target = MockTarget("test_file.py", "core.test_module", name="test_function", import_lines=["import pytest"])
    result = _target_block(target)
    assert result == 'File: test_file.py\nModule import path: core.test_module\nFunction: test_function\n\nUse exactly these imports (do not invent others for the target):\n```python\nimport pytest\nimport pytest\n```\n'

def test_characterize_target_block_empty_imports():
    target = MockTarget("test_file.py", "core.test_module", name="test_function", import_lines=[])
    result = _target_block(target)
    assert result == 'File: test_file.py\nModule import path: core.test_module\nFunction: test_function\n\nUse exactly these imports (do not invent others for the target):\n```python\nimport pytest\n```\n'

def test_characterize_target_block_with_class_name():
    target = MockTarget("test_file.py", "core.test_module", class_name="TestClass", name="test_method", import_lines=["import pytest"])
    result = _target_block(target)
    assert result == 'File: test_file.py\nModule import path: core.test_module\nMethod: TestClass.test_method\n\nUse exactly these imports (do not invent others for the target):\n```python\nimport pytest\nimport pytest\n```\n'

def test_characterize_target_block_no_class_name():
    target = MockTarget("test_file.py", "core.test_module", name="test_function", import_lines=["import pytest"])
    result = _target_block(target)
    assert result == 'File: test_file.py\nModule import path: core.test_module\nFunction: test_function\n\nUse exactly these imports (do not invent others for the target):\n```python\nimport pytest\nimport pytest\n```\n'