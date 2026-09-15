import pytest
from core._gaps_ref import main
import core._gaps_ref as _gaps_ref
import json



def test_characterize_main_invalid_json(tmp_path):
    cov_json = tmp_path / "coverage.json"
    cov_json.write_text("invalid json", encoding="utf-8")
    repo_root = str(tmp_path)
    with pytest.raises(json.JSONDecodeError):
        main(str(cov_json), repo_root)
