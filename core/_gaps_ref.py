"""실측 커버리지로 '미커버 라인이 어떻게 분포하는가'를 측정.
→ 함수 단위 타깃팅 vs 라인그룹 단위 타깃팅의 근거."""
import ast, json, sys, re
from pathlib import Path

def runs(nums):
    """연속 구간으로 묶기 -> [(start,end), ...]"""
    nums = sorted(nums); out = []
    for n in nums:
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [tuple(x) for x in out]

D_PATTERNS = [
    (re.compile(r'^\s*if\s+__name__'), "main_guard"),
    (re.compile(r'^\s*if\s+(t\.)?TYPE_CHECKING'), "type_checking"),
    (re.compile(r'^\s*raise\s+NotImplementedError'), "abstract"),
    (re.compile(r'^\s*\.\.\.\s*$'), "ellipsis"),
    (re.compile(r'^\s*pass\s*$'), "pass"),
    (re.compile(r'^\s*(import|from)\s'), "import"),
    (re.compile(r'^\s*raise\s*$'), "bare_reraise"),
    (re.compile(r'^\s*def\s|^\s*class\s|^\s*@'), "signature"),
]

def main(cov_json, repo_root):
    cov = json.loads(Path(cov_json).read_text())
    root = Path(repo_root).resolve()
    tot_stmt = tot_miss = 0
    fn_stats = []      # (file, fn, nlines, n_missing, n_runs, maxrun, fully_uncovered)
    d_counts = {}
    orphan_missing = 0   # 함수 밖(모듈 레벨) 미커버
    all_runs = []

    for relpath, data in cov["files"].items():
        p = (root / relpath)
        if not p.exists():
            p = Path(relpath)
            if not p.exists():
                continue
        src = p.read_text(encoding="utf-8", errors="replace")
        lines = src.splitlines()
        missing = set(data["missing_lines"])
        executed = set(data["executed_lines"])
        tot_stmt += data["summary"]["num_statements"]
        tot_miss += data["summary"]["missing_lines"]

        # D버킷 분류
        for ln in missing:
            if 1 <= ln <= len(lines):
                for rx, tag in D_PATTERNS:
                    if rx.match(lines[ln-1]):
                        d_counts[tag] = d_counts.get(tag, 0) + 1
                        break

        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        claimed = set()
        nested = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for ch in ast.walk(node):
                    if ch is not node and isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nested.add(ch.lineno)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.lineno in nested:
                continue
            end = getattr(node, "end_lineno", node.lineno)
            body_lo = node.body[0].lineno      # def/데코레이터 줄 제외 (import 시 실행됨)
            span = set(range(body_lo, end + 1))
            m = sorted(missing & span)
            claimed |= span
            if not m:
                continue
            rr = runs(m)
            all_runs += [b - a + 1 for a, b in rr]
            # 함수 전체가 미커버인가 = 실행된 문장이 하나도 없음
            fully = not (executed & span)
            fn_stats.append((relpath, node.name, end - node.lineno + 1,
                             len(m), len(rr), max(b - a + 1 for a, b in rr), fully))
        orphan_missing += len(missing - claimed)

    fn_stats.sort(key=lambda r: -r[3])
    miss_in_fn = sum(r[3] for r in fn_stats)
    fully_un = [r for r in fn_stats if r[6]]
    partial = [r for r in fn_stats if not r[6]]

    print(f"=== {root.name} ===")
    print(f"statements {tot_stmt}  missing {tot_miss}  coverage {100*(1-tot_miss/tot_stmt):.1f}%")
    print(f"미커버 라인 중 함수 내부 {miss_in_fn} ({100*miss_in_fn/max(tot_miss,1):.0f}%) / "
          f"모듈레벨 {orphan_missing} ({100*orphan_missing/max(tot_miss,1):.0f}%)")
    print()
    print(f"미커버를 가진 함수 {len(fn_stats)}개")
    print(f"  통째로 미커버(한 번도 호출 안 됨) {len(fully_un)}개 "
          f"= 미커버 라인의 {100*sum(r[3] for r in fully_un)/max(miss_in_fn,1):.0f}%")
    print(f"  부분 미커버(일부 분기만)         {len(partial)}개 "
          f"= 미커버 라인의 {100*sum(r[3] for r in partial)/max(miss_in_fn,1):.0f}%")
    print()
    if all_runs:
        all_runs.sort()
        print(f"연속 미커버 구간 {len(all_runs)}개")
        print(f"  구간 길이 p50={all_runs[len(all_runs)//2]} "
              f"p90={all_runs[int(len(all_runs)*.9)]} max={all_runs[-1]}")
        print(f"  길이 1~3줄 구간 비율 {100*sum(1 for x in all_runs if x<=3)/len(all_runs):.0f}%")
    print()
    print("함수당 미커버 라인 수 상위 15:")
    for r in fn_stats[:15]:
        kind = "전체미커버" if r[6] else "부분"
        print(f"  {r[3]:4d}줄 miss / {r[2]:4d}줄 fn / 구간{r[4]:2d}개 [{kind}] {r[0]}::{r[1]}")
    print()
    cum = 0; need = 0
    for i, r in enumerate(fn_stats):
        cum += r[3]
        if cum >= miss_in_fn * .5:
            need = i + 1; break
    print(f"미커버 라인의 50%를 덮으려면 상위 {need}개 함수 "
          f"({100*need/max(len(fn_stats),1):.0f}%)만 처리하면 됨")
    print()
    print("D버킷 후보(제외 가능) 미커버 라인:", sum(d_counts.values()),
          f"= 전체 미커버의 {100*sum(d_counts.values())/max(tot_miss,1):.0f}%")
    for k, v in sorted(d_counts.items(), key=lambda x: -x[1]):
        print(f"   {k:16s} {v}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
