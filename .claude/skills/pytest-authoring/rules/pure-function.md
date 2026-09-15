# 순수 함수

입력을 받아 값만 돌려주는 함수다. 가장 쉽고 ROI가 가장 높다.

- 입력을 3~4종류 고른다: **정상값 / 경계값 / 빈 값 / 잘못된 타입**
- 경계값을 반드시 하나 넣는다. `0`, `-1`, `""`, `[]`, `{}`, `None`, 최댓값
- 반환값 전체를 비교한다. `len(result)` 만 확인하지 않는다
- 입력 조합이 많으면 `@pytest.mark.parametrize` 로 한 함수에 묶는다

```python
import pytest
from src.billing import calc_fee

@pytest.mark.parametrize("amount,grade,expected", [
    (1000, "VIP", 850),
    (1000, "NORMAL", 1000),
    (0, "VIP", 0),
])
def test_calc_fee(amount, grade, expected):
    assert calc_fee(amount, grade) == expected
```

부동소수 비교는 `pytest.approx` 를 쓴다.
