"""구조 측정: 파일 단위 vs 함수 단위 타깃팅의 근거 수집."""
import ast, sys, os, json, statistics as st
from pathlib import Path

IO_NAMES = {"open","input","print","exit","quit"}
IO_MODULES = {"os","sys","socket","subprocess","requests","urllib","http","shutil",
              "pathlib","time","datetime","random","uuid","threading","asyncio",
              "sqlite3","logging","tempfile","pickle","json"}
PURE_OK = {"json","re","math","itertools","functools","collections","typing","enum","dataclasses"}

def tok(s):  # 대략적 토큰 추정
    return len(s) // 4

class FnInfo:
    __slots__ = ("file","name","lineno","end","nlines","branches","args","decorators",
                 "io","module_level_deps","is_method","src")

def module_level_effects(tree):
    """import/def/class/상수대입 외의 모듈 레벨 실행문 개수."""
    n = 0
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef, ast.Pass)):
            continue
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            val = node.value
            # 상수/리터럴/단순 이름 대입은 부작용 아님
            if val is None or isinstance(val, (ast.Constant, ast.Name, ast.Tuple,
                                               ast.List, ast.Dict, ast.Set,
                                               ast.Lambda, ast.BinOp, ast.JoinedStr)):
                continue
            n += 1  # 함수 호출 결과 대입 = import 시점 부작용 후보
            continue
        if isinstance(node, ast.If):
            # if TYPE_CHECKING / if __name__ 은 제외
            continue
        if isinstance(node, (ast.Try, ast.Expr, ast.With, ast.For, ast.While)):
            n += 1
    return n

def analyze_file(path, root):
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return [], None
    lines = src.splitlines()
    mle = module_level_effects(tree)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        f = FnInfo()
        f.file = str(Path(path).relative_to(root)).replace("\\", "/")
        f.name = node.name
        f.lineno, f.end = node.lineno, end
        f.nlines = end - node.lineno + 1
        f.branches = sum(1 for x in ast.walk(node)
                         if isinstance(x, (ast.If, ast.For, ast.While, ast.Try,
                                           ast.BoolOp, ast.IfExp, ast.ExceptHandler)))
        f.args = len(node.args.args) + len(node.args.kwonlyargs)
        f.decorators = len(node.decorator_list)
        f.is_method = False
        io = set()
        for x in ast.walk(node):
            if isinstance(x, ast.Call):
                fn = x.func
                if isinstance(fn, ast.Name) and fn.id in IO_NAMES:
                    io.add(fn.id)
                elif isinstance(fn, ast.Attribute):
                    base = fn.value
                    if isinstance(base, ast.Name) and base.id in IO_MODULES and base.id not in PURE_OK:
                        io.add(f"{base.id}.{fn.attr}")
        f.io = sorted(io)
        f.module_level_deps = mle
        f.src = "\n".join(lines[node.lineno-1:end])
        out.append(f)
    # 메서드 표시
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for f in out:
                        if f.lineno == b.lineno:
                            f.is_method = True
    return out, (str(Path(path).relative_to(root)).replace("\\","/"), len(lines), mle, len(out))

def main(repo, pkg):
    root = Path(repo).resolve()
    src_root = root / pkg
    fns, files = [], []
    for p in src_root.rglob("*.py"):
        s = str(p).replace("\\","/")
        if "/test" in s or "/_vendor/" in s:
            continue
        a, fi = analyze_file(p, root)
        fns += a
        if fi: files.append(fi)

    sizes = sorted(f.nlines for f in fns)
    per_file_tokens = [tok(Path(root/f[0]).read_text(encoding="utf-8", errors="replace")) for f in files]
    per_fn_tokens = [tok(f.src) for f in fns]

    pure = [f for f in fns if not f.io]
    ioful = [f for f in fns if f.io]
    big = [f for f in fns if f.nlines > 60]
    mle_files = [f for f in files if f[2] > 0]

    def pct(v, p): return v[int(len(v)*p)] if v else 0
    r = {
        "repo": root.name, "files": len(files), "functions": len(fns),
        "fn_lines_p50": pct(sizes,.5), "fn_lines_p90": pct(sizes,.9), "fn_lines_p99": pct(sizes,.99),
        "fn_lines_max": sizes[-1] if sizes else 0,
        "fn<=30lines_%": round(100*sum(1 for s in sizes if s<=30)/max(len(sizes),1),1),
        "fn<=60lines_%": round(100*sum(1 for s in sizes if s<=60)/max(len(sizes),1),1),
        "file_tokens_p50": pct(sorted(per_file_tokens),.5),
        "file_tokens_p90": pct(sorted(per_file_tokens),.9),
        "file_tokens_max": max(per_file_tokens) if per_file_tokens else 0,
        "fn_tokens_p50": pct(sorted(per_fn_tokens),.5),
        "fn_tokens_p90": pct(sorted(per_fn_tokens),.9),
        "fn_tokens_max": max(per_fn_tokens) if per_fn_tokens else 0,
        "file_tokens>4k_%": round(100*sum(1 for t in per_file_tokens if t>4000)/max(len(per_file_tokens),1),1),
        "fn_tokens>2k_%": round(100*sum(1 for t in per_fn_tokens if t>2000)/max(len(per_fn_tokens),1),1),
        "pure_fn_%": round(100*len(pure)/max(len(fns),1),1),
        "io_fn_%": round(100*len(ioful)/max(len(fns),1),1),
        "big_fn(>60)_%": round(100*len(big)/max(len(fns),1),1),
        "lines_in_big_fn_%": round(100*sum(f.nlines for f in big)/max(sum(sizes),1),1),
        "files_with_import_side_effects": len(mle_files),
        "files_with_import_side_effects_%": round(100*len(mle_files)/max(len(files),1),1),
        "avg_fn_per_file": round(len(fns)/max(len(files),1),1),
        "branches_p50": pct(sorted(f.branches for f in fns),.5),
        "branches_p90": pct(sorted(f.branches for f in fns),.9),
    }
    return r

if __name__ == "__main__":
    rows = [main(*a.split(":")) for a in sys.argv[1:]]
    keys = list(rows[0].keys())
    w = max(len(k) for k in keys)
    print(f"{'metric'.ljust(w)} | " + " | ".join(f"{r['repo']:>10}" for r in rows))
    print("-"*(w+3+13*len(rows)))
    for k in keys[1:]:
        print(f"{k.ljust(w)} | " + " | ".join(f"{str(r[k]):>10}" for r in rows))
