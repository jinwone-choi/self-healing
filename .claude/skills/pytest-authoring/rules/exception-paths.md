# 예외 경로

미커버 라인의 상당수가 `except` 블록이다. **정상 경로보다 입력 만들기가 쉬워 ROI가 높다.**

```python
import pytest
from src.parser import parse_config

def test_parse_config_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        parse_config("")
```

- `pytest.raises` 에 **`match=` 를 반드시 넣는다.** 없으면 엉뚱한 이유로 난 같은 타입의
  예외도 통과해 버린다
- 예외를 삼키고 기본값을 돌려주는 코드는 `raises` 가 아니라 **반환값**을 검증한다

```python
def test_returns_default_on_broken_json(monkeypatch, tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{oops")
    assert load_settings(p) == {}          # except 블록이 여기서 덮인다
```

- 예외를 유발하는 가장 싼 방법: 잘못된 타입 1개, `None`, 빈 컬렉션, 존재하지 않는 경로
- `except Exception: raise` 처럼 재전파만 하는 줄은 덮지 말고 `pragma: no cover` 대상이다
