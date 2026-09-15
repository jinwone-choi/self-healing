# 클래스 · 상태

```python
def test_counter_increments():
    c = Counter(start=5)
    c.add(3)
    assert c.value == 8
```

- 생성자가 값 대입만 하면 그냥 인스턴스화한다
- 생성자가 외부 연결을 하면 **그 의존만 monkeypatch** 하고 인스턴스를 만든다.
  그래도 안 되면 테스트를 짜지 말고 "생성자에서 외부 연결" 사유로 보고한다
- 상태 변경 메서드는 **동작 전/후를 모두 단언한다**

```python
def test_reset_clears_items():
    c = Cart(); c.add("a")
    assert len(c.items) == 1        # 전
    c.reset()
    assert c.items == []            # 후
```

- 모듈 전역 캐시/싱글턴을 쓰는 코드는 테스트 간 간섭이 생긴다.
  fixture로 매번 초기화한다

```python
@pytest.fixture(autouse=True)
def _clear_cache():
    src.cache.CACHE.clear()
    yield
    src.cache.CACHE.clear()
```

- 프라이빗 메서드(`_foo`)는 직접 테스트하지 않는다. 공개 메서드를 통해 덮는다
