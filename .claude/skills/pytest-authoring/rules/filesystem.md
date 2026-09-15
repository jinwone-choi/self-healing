# 파일 · 프로세스

파일은 **모킹하지 말고 `tmp_path` 에 진짜로 만든다.** 모킹보다 쉽고 안정적이다.

```python
def test_load_settings(tmp_path):
    p = tmp_path / "app.yml"
    p.write_text("name: test\n", encoding="utf-8")
    assert load_settings(p)["name"] == "test"
```

- `tmp_path` 는 `pathlib.Path` 다. 테스트마다 새로 만들어지고 자동 정리된다
- 함수가 경로를 인자로 안 받고 상수를 쓰면 그 상수를 monkeypatch 한다
- 인코딩을 항상 명시한다 (`encoding="utf-8"`). Windows 기본값 때문에 깨진다
- 현재 작업 디렉터리에 의존하면 `monkeypatch.chdir(tmp_path)`

`subprocess` 는 실제로 실행하지 않는다.

```python
def test_git_rev(monkeypatch):
    import src.vcs as vcs
    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="abc123\n", stderr="")
    monkeypatch.setattr(vcs.subprocess, "run", lambda *a, **k: fake)
    assert vcs.current_rev() == "abc123"
```

네트워크 호출은 어떤 경우에도 하지 않는다. 하네스가 소켓을 차단하므로 실행 시 실패한다.
