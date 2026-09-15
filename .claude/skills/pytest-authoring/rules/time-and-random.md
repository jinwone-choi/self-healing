# 시간 · 난수 · UUID

결정적이어야 한다. 실제 시각이나 난수에 의존하면 언젠가 반드시 깨진다.

```python
import datetime as dt
import src.report as report

def test_uses_fixed_now(monkeypatch):
    class FixedDatetime(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 1, 15, 9, 0, 0)
    monkeypatch.setattr(report.datetime, "datetime", FixedDatetime)
    assert report.build_title() == "2026-01 리포트"
```

- `time.time` / `time.sleep` : `monkeypatch.setattr(mod.time, "time", lambda: 1700000000.0)`
  `sleep` 은 no-op(`lambda s: None`)으로 바꾼다. 느린 테스트가 즉시 끝난다
- `random` : `random.seed(0)` 보다 `monkeypatch.setattr(mod.random, "choice", lambda s: s[0])`
  처럼 함수를 고정하는 쪽이 구현 변경에 덜 민감하다
- `uuid.uuid4` : 고정 UUID를 돌려주는 람다로 교체

절대 쓰지 않는다: `assert result.timestamp > 0` 같은 느슨한 단언, 실제 `sleep`.
