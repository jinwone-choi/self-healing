# 테스트 불가능 케이스 카탈로그 & 리팩터링 전략

전제: 파이프라인은 **business code를 절대 수정하지 않는다.**
그래서 이 문서의 목적은 "무엇을 포기하고, 무엇을 우회하고, 무엇을 **사람에게 제안**할지"를
미리 분류해 두는 것이다.

---

## 0. 순서가 전부다 — 리팩터링과 테스트의 닭-달걀 문제

> "unit test를 만들기 위한 refactoring이 필요한데, 그건 어떻게 해야 할지 모르겠다"

이게 레거시 코드 작업의 고전적 교착이고, 해법은 정해져 있습니다. **순서를 뒤집는 것**입니다.

```
❌ 틀린 순서:  리팩터링 → 테스트 작성
               (안전망 없이 수술. 뭐가 깨졌는지 알 방법이 없음)

✅ 맞는 순서:  ① 현재 동작을 그대로 박제하는 characterization test (커버 가능한 만큼)
               ② 그 테스트를 안전망 삼아 최소 침습 리팩터링 (사람이, 리뷰받고)
               ③ 새로 열린 부분에 대해 파이프라인 재실행
               ④ ①의 characterization test를 제대로 된 테스트로 승격
```

핵심은 **①이 100%일 필요가 없다**는 점입니다. 60%만 덮여 있어도 "리팩터링 후 그 60%가
그대로 통과한다"는 사실은 강력한 신호입니다. 그래서 파이프라인의 1차 목표는
"80% 달성"이 아니라 **"②를 시작할 수 있을 만큼의 안전망 확보"**로 보는 게 맞습니다.

그리고 ②는 **자동화하지 않습니다.** 파이프라인은 리팩터링을 하지 않고
`reports/refactor_proposals.md` 를 냅니다. 각 제안에는 다음이 붙습니다.

```
모듈/함수      : src/report.py :: build_monthly_report
막힌 이유      : 함수 내부에서 datetime.now() 직접 호출 + DB 커넥션 생성
제안 수술      : 기본 인자 주입 (seam #2)
변경 라인 수   : 2
호출부 영향    : 없음 (기본값 유지, 하위 호환)
예상 획득      : 미커버 47라인 중 41라인
Before/After   : (아래 패치 형태로 제시)
```

**변경 라인 수 대비 예상 커버리지 획득량**으로 정렬해서 보여주면, 사람이 "이건 2줄이니
하자 / 이건 80줄이니 나중에"를 데이터로 판단할 수 있습니다. 이게 이 도구의 진짜 가치일
수 있습니다 — 커버리지를 올리는 것보다, **어디를 고쳐야 올릴 수 있는지 알려주는 것.**

---

## 1. 분류 체계

모든 타깃을 세 버킷으로 나눕니다. AST 분석 단계(Phase 2)에서 자동 판정합니다.

| 버킷 | 의미 | 파이프라인 동작 |
|---|---|---|
| **A** | 소스 수정 없이 테스트 가능 | 자동 생성 대상 |
| **B** | 기술적으로 가능하나 자동 생성 범위 밖 | 스킵 + `manual_review` 목록 |
| **C** | 리팩터링 없이는 불가능 | 스킵 + `refactor_proposals.md` |
| **D** | 애초에 테스트할 가치 없음 | `# pragma: no cover` 후보로 제안 |

**중요**: 많은 사람이 C로 착각하는 것들이 실제로는 A입니다.
`monkeypatch`의 힘을 과소평가하면 멀쩡한 타깃을 버리게 됩니다. 아래 표에서 A가 많은 이유입니다.

---

## 2. 버킷 A — 소스 수정 없이 가능 (파이프라인이 처리)

### A-1. 모듈 전역 클라이언트/싱글턴

```python
# src/api.py
client = SomeClient(host=os.environ["API_HOST"])   # import 시점에 생성

def fetch_user(uid):
    return client.get(f"/users/{uid}")
```

**되는 이유**: 전역 이름은 monkeypatch로 교체 가능합니다.

```python
def test_fetch_user(monkeypatch):
    fake = types.SimpleNamespace(get=lambda path: {"id": 1, "path": path})
    monkeypatch.setattr(api, "client", fake)
    assert api.fetch_user(1)["id"] == 1
```

⚠️ 단, `os.environ["API_HOST"]`가 **import 시점에** 터지면 A가 아니라 C-1입니다.

### A-2. 함수 내부에서 호출하는 import된 함수

```python
from utils import send_mail
def notify(u): send_mail(u.email, "hi")
```

`monkeypatch.setattr(mymodule, "send_mail", fake)` — **정의된 모듈이 아니라 사용하는 모듈**에
패치해야 합니다. 소형 모델이 자주 틀리는 부분이라 rule card로 명시했습니다.

### A-3. 시간 / 난수 / UUID

`datetime.now`, `time.time`, `time.sleep`, `random.*`, `uuid.uuid4` — 전부 monkeypatch 가능.
`time.sleep`을 no-op으로 바꾸면 느린 테스트도 즉시 끝납니다.

### A-4. 환경변수 / 설정

`monkeypatch.setenv`, `monkeypatch.delenv`. 함수 실행 시점에 읽는 경우에 한해 A.

### A-5. 파일 I/O

`tmp_path` fixture로 실제 파일을 만들어 씁니다. 모킹보다 실파일이 쉽고 안정적입니다.

### A-6. subprocess / 외부 바이너리

`monkeypatch.setattr(subprocess, "run", fake)` 로 `CompletedProcess`를 흉내냅니다.

### A-7. 예외 경로

`pytest.raises`. 미커버 라인의 상당수가 `except` 블록이고, **여기가 ROI가 가장 좋습니다.**
정상 경로보다 입력 만들기가 쉬운 경우가 많습니다(잘못된 타입 하나 넣으면 끝).

### A-8. 클래스 메서드 (생성자가 가벼울 때)

`__init__`이 값 대입만 하면 그냥 인스턴스화해서 테스트합니다.

---

## 3. 버킷 B — 가능하지만 자동화 범위 밖

| 케이스 | 왜 밖인가 | 어떻게 할 것인가 |
|---|---|---|
| **웹 프레임워크 엔드포인트** (Django view, FastAPI route) | `TestClient`/`django.test` fixture와 앱 설정·DB 픽스처가 필요. 프레임워크마다 관례가 다름 | 프레임워크별 conftest 템플릿을 사람이 1회 작성하면 그 뒤로는 A로 내려옴. **투자 대비 효과가 가장 큰 항목** |
| **DB 연동 코드** | 스키마·마이그레이션·트랜잭션 격리 필요 | 테스트용 sqlite 또는 testcontainers를 사람이 셋업. 이후 A |
| **async 함수** | `pytest-asyncio` 설정 + 이벤트 루프 관리 | `asyncio_mode=auto` 설정만 사람이 넣으면 대부분 A로 내려옴 |
| **동적 디스패치** (`getattr(self, "handle_"+kind)`, 메타클래스, 데코레이터 팩토리) | 정적 분석으로 호출 그래프를 못 그림. 모델도 이해 못 함 | 사람이 직접. 자동 생성 시도 자체를 하지 않는 게 낫습니다 |
| **멀티스레드/경합 로직** | 비결정적. flaky 테스트 양산 | 로직만 동기 함수로 추출(C-5) 후 그 함수를 테스트 |

---

## 4. 버킷 C — 리팩터링 필요 (제안만 생성)

### C-1. import 시점 부작용 ★ 가장 치명적

```python
# src/config.py
DB = psycopg2.connect(os.environ["DSN"])      # import 하는 순간 DB 접속
SETTINGS = yaml.safe_load(open("/etc/app.yml"))
```

**왜 치명적인가**: 이 모듈을 import하는 **모든 모듈**이 테스트 불가가 됩니다.
한 파일의 문제가 repo 전체로 전염됩니다. 커버리지가 40%대에서 안 오르는 repo는
열에 아홉 이 문제입니다.

**수술 — Lazy init (seam #3)**

```python
# before
DB = psycopg2.connect(os.environ["DSN"])

# after — 호출부 수정 불필요하게 하려면 함수로 감싸고 캐시
_DB = None
def get_db():
    global _DB
    if _DB is None:
        _DB = psycopg2.connect(os.environ["DSN"])
    return _DB
```

호출부가 `config.DB`를 직접 쓰고 있다면 호출부도 바뀌므로 변경 범위가 커집니다.
제안서에 **영향받는 호출부 개수**를 반드시 같이 적습니다.

### C-2. 생성자에서 외부 연결

```python
class Reporter:
    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn)     # 인스턴스를 못 만듦 → 모든 메서드 테스트 불가
```

**수술 — 의존성 주입 (seam #2)**. 기본값을 유지해 하위 호환을 지킵니다.

```python
class Reporter:
    def __init__(self, dsn, connector=psycopg2.connect):
        self.conn = connector(dsn)
```

호출부는 한 글자도 안 바뀝니다. **변경 1줄, 리스크 최소.** 제안 1순위 패턴입니다.

### C-3. 거대 함수

200줄 · 분기 25개짜리 함수는 이론상 테스트 가능하지만 실질적으로 불가능합니다.
입력 조합이 폭발하고, 소형 모델은 프롬프트에 함수 전문을 넣는 것조차 buffer를 넘깁니다.

**수술 — Extract function (seam #1)**. 분기 덩어리를 순수 함수로 떼어냅니다.
떼어낸 함수는 즉시 버킷 A가 되고, 보통 **전체 미커버 라인의 70% 이상**이 여기 있습니다.

### C-4. `while True` 데몬 루프

```python
def run():
    while True:
        job = queue.get()
        process(job)          # ← 정작 테스트하고 싶은 건 이것
        time.sleep(5)
```

테스트하면 영원히 안 끝납니다(파이프라인은 타임아웃으로 폐기).

**수술 — 루프 본문 추출**. `run()`은 얇은 껍데기로 남기고 `# pragma: no cover`,
`process_one()`을 테스트합니다. 이게 seam의 가장 교과서적인 예입니다.

### C-5. 계산과 부작용의 혼재

```python
def process_and_save(path):
    data = json.load(open(path))
    result = <30줄의 복잡한 계산>
    db.insert(result)
    send_slack(result)
```

**수술 — Command/Query 분리 (seam #5)**. 계산부를 `compute(data) -> result` 순수 함수로
분리하면 그 30줄이 통째로 버킷 A가 됩니다. **커버리지 획득량이 가장 큰 수술**입니다.

### C-6. 전역 mutable 상태

모듈 전역 `CACHE = {}` 를 여러 함수가 공유하면 테스트 간섭이 생깁니다.
→ 우회는 가능합니다(autouse fixture로 매 테스트마다 리셋). 우회가 되면 A로 내립니다.
우회가 어려운 경우(클래스 변수 누적 등)만 C.

---

## 5. 버킷 D — 커버하지 말아야 할 것

무리하게 덮으면 **가치 없는 테스트로 분모만 채우는 꼴**이 됩니다.

| 대상 | 처리 |
|---|---|
| `if __name__ == "__main__":` | `pragma: no cover` |
| `argparse` 기반 `main()` 의 인자 파싱 배선 | `pragma: no cover` (로직은 분리 후 테스트) |
| 방어적 `except Exception: raise` 재전파 | `pragma: no cover` |
| `@abstractmethod` 본문, `Protocol` 정의, `...` | coverage 설정의 `exclude_lines` |
| `TYPE_CHECKING` 블록 | `exclude_lines` |
| 자동 생성 코드 (protobuf, ORM 마이그레이션) | `omit` 에서 제외 |
| C 확장 / Cython | coverage 측정 자체가 안 됨 → `omit` |
| GUI / 하드웨어 / 직렬포트 / GPU 커널 | 어댑터 계층으로 밀어내고 어댑터만 `no cover` |

**먼저 할 일**: 파이프라인을 돌리기 전에 `.coveragerc` 의 `omit` / `exclude_lines` 를 정리합니다.
LLM 호출이 필요 없으므로 공짜입니다.

⚠️ **다만 효과는 크지 않습니다(실측).** click 실측에서 D버킷 후보는 미커버 631줄 중 40줄(6%),
커버리지로는 **약 0.8%p** 상승에 그쳤습니다. 이전에 "5~15%p"로 추정했던 것은 과장이었습니다.
분모 정리로 80% 게이트를 넘기려는 기대는 버리고, 잡음 제거 목적으로만 하십시오.
근거: `docs/DECISIONS.md` D7.

---

## 6. 5가지 표준 수술 (seam) 요약

리팩터링 제안은 이 다섯 가지 중 하나로만 생성합니다. 패턴을 고정해야
사람이 리뷰하기 쉽고, 제안의 품질이 일정합니다.

| # | 이름 | 변경 규모 | 호출부 영향 | 커버리지 획득 |
|---|---|---|---|---|
| 1 | **Extract function** — 분기 덩어리/루프 본문을 순수 함수로 | 중 | 없음 | 매우 큼 |
| 2 | **Parameterize dependency** — 기본 인자로 의존 주입 | **1~2줄** | **없음** | 큼 |
| 3 | **Lazy init** — import 시점 → 최초 사용 시점 | 소~중 | 있을 수 있음 | 매우 큼 (전염 차단) |
| 4 | **Extract adapter** — 하드웨어/외부 I-O를 얇은 층으로 격리 | 대 | 있음 | 중 (분모 정리 효과) |
| 5 | **Split command/query** — 계산과 부작용 분리 | 중 | 없음 | 매우 큼 |

**권장 착수 순서: 2 → 1 → 5 → 3 → 4.**
2번은 1~2줄에 호출부 영향이 없어 리뷰 통과가 쉽습니다. 작은 성공을 먼저 쌓는 게
조직 내에서 이 작업을 계속할 수 있게 만듭니다.
