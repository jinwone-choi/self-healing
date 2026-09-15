import pytest
from core._gaps_ref import main
import core._gaps_ref as _gaps_ref
import json


def test_characterize_main_invalid_syntax(tmp_path, monkeypatch):
    cov_json = tmp_path / "coverage.json"
    cov_json.write_text(json.dumps({
        "files": {
            "invalid_file.py": {
                "missing_lines": [1],
                "executed_lines": [],
                "summary": {
                    "num_statements": 1,
                    "missing_lines": 1
                }
            }
        }
    }), encoding="utf-8")
    
    monkeypatch.setattr(_gaps_ref, "ast", None)  # Simulate import failure
    repo_root = str(tmp_path)
    with pytest.raises(ZeroDivisionError):
        main(str(cov_json), repo_root)