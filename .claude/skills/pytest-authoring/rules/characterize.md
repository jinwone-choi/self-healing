# characterization 모드

**기대값을 예측하지 마라. 하네스가 실행 결과로 단언을 생성한다.**

너의 역할은 **호출부만** 쓰는 것이다.

```python
def test_characterize_calc_fee_vip():
    result = calc_fee(1000, "VIP")
    assert result == __CAPTURE__          # 이 자리는 하네스가 채운다
```

- 단언 우변에 반드시 `__CAPTURE__` 를 쓴다. 숫자나 문자열을 직접 적지 않는다
- 함수 이름은 `test_characterize_` 로 시작한다
- 대신 **입력의 다양성**에 집중한다. 서로 다른 코드 경로를 지나가는 입력을 고른다:
  정상값 / 경계값 / 빈 값 / 조건 분기의 각 갈래
- 예외가 날 것 같은 입력은 이렇게 쓴다

```python
def test_characterize_calc_fee_negative():
    with pytest.raises(__CAPTURE_EXC__):
        calc_fee(-1, "VIP")
```

- 부작용이 있는 함수(파일 쓰기·전역 변경)는 이 모드에서 다루지 않는다. 보고하고 넘긴다

> 이렇게 만든 테스트는 **현재 동작을 기록한 것이지 정답을 검증한 것이 아니다.**
> 리팩터링 시 회귀 방지에는 유효하지만, 기존 버그도 함께 박제된다.
