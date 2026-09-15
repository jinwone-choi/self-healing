# monkeypatch — 어디에 붙일 것인가

**가장 많이 틀리는 지점이다. 정의된 모듈이 아니라 _사용하는_ 모듈에 패치한다.**

```python
# src/notify.py
from utils.mailer import send_mail      # 여기로 이름이 복사됐다

def notify(user):
    send_mail(user.email, "hi")
    return True
```

```python
# ✅ 맞다 — 사용하는 모듈(src.notify)의 이름을 바꾼다
import src.notify as notify

def test_notify(monkeypatch):
    calls = []
    monkeypatch.setattr(notify, "send_mail", lambda to, msg: calls.append(to))
    assert notify.notify(User(email="a@b.c")) is True
    assert calls == ["a@b.c"]

# ❌ 틀리다 — 이미 복사된 이름은 안 바뀐다
monkeypatch.setattr("utils.mailer.send_mail", fake)
```

- 모듈 전역 객체(`client`, `conn`, `CACHE`)도 같은 방식으로 교체한다
- 가짜 객체는 `types.SimpleNamespace` 나 작은 클래스로 만든다. `unittest.mock` 없이도 된다
- **호출 여부만이 아니라 전달된 인자를 검증한다.** 리스트에 담아 assert 한다
