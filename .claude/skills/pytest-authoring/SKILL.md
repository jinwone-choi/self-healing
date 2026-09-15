---
name: pytest-authoring
description: Write pytest unit tests for an existing Python codebase without modifying business logic. Use when adding tests to legacy/untested code, raising coverage, judging whether a target is testable as-is, or deciding what refactoring a target needs first. Also the rule source injected into the automated coverage pipeline's LLM prompts.
---

# pytest 테스트 작성 규칙

이 skill은 **두 소비자**를 위한 단일 규칙 저장소다.

| 소비자 | 읽는 방식 | 컨텍스트 |
|---|---|---|
| Claude Code (사람과 대화) | 이 파일 전체 + 필요한 rule card | 넉넉함 |
| 자동 파이프라인의 사내 LLM (gemma) | 오케스트레이터가 **타깃 유형에 맞는 card 1~2장만** 프롬프트에 삽입 | 4K 토큰 |

그래서 규칙은 **짧은 카드로 쪼개 `rules/` 에 둔다.** 이 파일에 규칙 본문을 쌓지 않는다.
gemma에 전문을 넣을 수 없기 때문이다.

---

## 1. 절대 규칙 (예외 없음)

1. **`tests/` 밖의 파일을 수정하지 않는다.** 테스트가 실패하면 테스트를 고친다.
   소스의 버그로 보이면 `@pytest.mark.xfail(reason=...)` 로 표시하고 보고한다.
2. **테스트는 결정적이어야 한다.** 실행 순서·시각·난수·네트워크에 의존하지 않는다.
3. **모든 테스트 함수에 실제 동작을 검증하는 단언이 있어야 한다.**
   호출만 하고 끝나는 테스트는 커버리지 숫자만 올리고 가치가 0이다.
4. **테스트 하나는 한 가지를 검증한다.** 실패했을 때 무엇이 깨졌는지 이름만 보고 알 수 있어야 한다.

---

## 2. 규칙을 두 종류로 나눈다 — 이 skill의 핵심 설계

약한 모델은 프롬프트의 산문 규칙을 **지키지 않는다.** 그래서 규칙을 이렇게 배치한다.

| 종류 | 어디에 두는가 | 예 |
|---|---|---|
| **기계 검증 가능** | `core/validate.py` (프롬프트 아님) | assert 존재, `assert True` 금지, `tests/` 외 쓰기 금지, import 성공, 30초 타임아웃, flaky 2회 검증 |
| **판단이 필요** | rule card (프롬프트에 삽입) | 어떤 입력을 고를 것인가, 어디를 patch할 것인가, 무엇을 검증할 가치가 있는가 |

**"프롬프트에 써서 부탁할 수 있는 것"과 "코드로 강제할 수 있는 것"이 있으면 항상 후자를 택한다.**
프롬프트 규칙이 늘어날수록 gemma의 컨텍스트만 먹고 준수율은 떨어진다.

---

## 3. rule card 선택 (오케스트레이터가 자동)

Phase 2의 AST 분석이 타깃 유형을 판정하고, 해당 카드만 주입한다.

| 타깃 유형 판정 조건 | 주입할 card |
|---|---|
| I/O 의존 없음, 인자로만 계산 | `pure-function.md` |
| `datetime` / `time` / `random` / `uuid` 사용 | `time-and-random.md` |
| import된 함수·전역 객체를 호출 | `patching.md` |
| `raise` / `except` 가 미커버 라인에 포함 | `exception-paths.md` |
| `open` / `Path` / `subprocess` 사용 | `filesystem.md` |
| 클래스 메서드 | `class-and-state.md` |
| 항상 (모드가 characterize일 때) | `characterize.md` |

**최대 2장까지만.** 3장 이상 넣으면 프롬프트가 길어져 gemma의 지시 준수율이 떨어진다.

---

## 4. 카드를 추가·수정하는 규칙

카드는 직관으로 늘리지 않는다. **실측으로 검증한 것만 남긴다.**

```
1. 실패 로그를 유형별로 집계한다 (reports/metrics.json 의 failure_kind)
2. 상위 실패 유형 하나를 겨냥한 카드를 쓴다 (200 토큰 이내)
3. 순수 함수 30개 고정 세트에 대해 카드 有/無 A/B 실행
4. 통과율이 유의하게 오르면 채택, 아니면 폐기
```

카드가 많아질수록 좋아지는 게 아니다. 카드 하나는 다른 카드의 자리를 뺏는다.
`rules/_metrics.md` 에 각 카드의 채택 근거 수치를 기록한다.

---

## 5. 좋은 테스트의 판정 기준

파이프라인이 자동 집계하는 지표. 커버리지 %만 보면 안 된다.

| 지표 | 기준 | 왜 |
|---|---|---|
| 단언 밀도 | 테스트 함수당 assert ≥ 1, 평균 ≥ 1.5 | 호출만 하는 테스트 배제 |
| 경계값 비율 | 타깃당 최소 1개는 경계/예외 입력 | 행복 경로만 덮는 것 방지 |
| mutation score | 상위 모듈 표본 대상 (선택) | **커버리지가 거짓말하는지 아는 유일한 방법** |
| 실행 시간 | 테스트당 < 1초 | 느린 스위트는 아무도 안 돌린다 |
| flaky | 2회 연속 동일 결과 | 비결정성 조기 차단 |
| characterize 비율 | 리포트에 명시 | 이 비율이 높으면 "회귀 방지용"이지 "정답 검증"이 아님 |

마지막 항목이 중요하다. characterization test는 **현재 동작을 정답으로 고정**하므로,
버그가 있으면 버그를 박제한다. 커버리지 80%를 보고할 때 이 비율을 같이 보고하지 않으면
숫자가 사람을 속인다.

---

## 6. 테스트를 쓰기 전에 테스트 가능성부터 판정한다

억지로 짜지 않는다. 막혔으면 **왜 막혔는지**를 리포트한다.
분류 체계와 5가지 표준 수술(seam)은 `docs/TESTABILITY.md` 참조.

```
A: 소스 수정 없이 가능       → 지금 쓴다
B: 가능하나 셋업이 필요       → conftest 템플릿을 사람에게 요청
C: 리팩터링 필요             → 수술 종류 + 변경 라인 수 + 예상 획득량을 제안서로
D: 커버할 가치 없음          → pragma: no cover 제안
```
