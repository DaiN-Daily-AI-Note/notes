"""네온 vs 카본 직접 시험 도구 (pstack blast-radius 재설계, 2026-11-19).

    python3 lab.py new <폴더> <팔>                       새 실행 폴더 + 배정 기록(팔은 여기서만 정함)
    python3 lab.py grade <폴더> <A|B> --start HH:MM:SS --end HH:MM:SS --interventions N
                         [--quota-before X --quota-after Y --quota-bucket 이름] [--redo]
    python3 lab.py selftest                              채점기 허점 회귀 시험(속임수 사례로)
    python3 lab.py decide                                사전 등록 규칙대로 판정 한 줄

판정이 틀릴 수 있는 길과 막는 장치(설계: DESIGN.md '판정 오류 막기'):
- 보이는 시험은 모델의 tests/가 아니라 원본 tests/로, 모델이 만든 ledger/만 가져와 돌린다(시험 고치기·건너뛰기 무력화).
- 채점은 자식 프로세스 + 시간 제한(무한 루프에 안 멈춤).
- 과제가 끝난 순간 폴더를 스냅숏으로 복사해 그걸 채점한다(B가 A를 덮어써도 A 점수는 그대로).
- 팔 이름은 대화가 아니라 new 때 쓴 배정 파일에서 읽는다(받아 적기 실수 차단).
- 시간은 시작·끝 시각으로 받고 계산은 코드가 한다. 끝 시각 뒤에 파일이 바뀌었으면 표시한다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "ledger-tools"
RUNS = Path(os.environ.get("LAB_RUNS", HERE / "results" / "runs"))
RESULTS = Path(os.environ.get("LAB_RESULTS", HERE / "results" / "results.jsonl"))
STUDIO = Path(os.environ.get("LAB_STUDIO", Path.home() / "Studio"))
PY = os.environ.get("LAB_PY", sys.executable)  # 공개판: 실행 중인 파이썬(원래 시험은 /usr/local/bin/python3 3.12)
ARMS = ("gemini-4-neon", "gemini-4-carbon", "orchestrator-neon")
TIMEOUT = 60
INSTRUCTION_FILES = ("AGENTS.md", "GEMINI.md", "CLAUDE.md", ".agents", ".gemini")
KST = dt.timezone(dt.timedelta(hours=9))
AG_BRAIN = Path(os.environ.get("LAB_AG_BRAIN", Path.home() / ".gemini" / "antigravity" / "brain"))
PROMPT_A = "테스트가 3개 실패해요. 원인 찾아서 고쳐 주고, 다 통과하는지 확인해 줘."
PROMPT_B = "README '할 일'에 있는 월별 요약 기능 만들어 줘. 테스트도 같이 추가해 줘."
# 백만 토큰당 달러. 원문: https://ai.google.dev/gemini-api/docs/pricing (2026-11-19 확인)
# 카본은 11-30까지 2/10/0.10, 12-01부터 4/20/0.20. 네온 3/15/0.15. 출력값은 생각 토큰 포함.
PRICES = {
    "nov": {"gemini-4-carbon": (2.00, 10.00, 0.10), "gemini-4-neon": (3.00, 15.00, 0.15)},
    "dec": {"gemini-4-carbon": (4.00, 20.00, 0.20), "gemini-4-neon": (3.00, 15.00, 0.15)},
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _original_tests() -> dict[str, str]:
    return {p.name: _sha(p) for p in sorted((FIXTURE / "tests").glob("test_*.py"))}


def _expected_visible() -> int:
    """원본 시험 메서드 수(파일 수가 아니라). 2026-11-19 selftest가 파일 수(3)와 비교하던 버그를 잡음."""
    return sum(len(re.findall(r"^\s+def test_", p.read_text(encoding="utf-8"), re.M))
               for p in (FIXTURE / "tests").glob("test_*.py"))


def grade_snapshot(snap: Path, task: str) -> dict:
    """스냅숏 폴더를 채점한다. 모델 코드는 ledger/만 쓴다."""
    out: dict = {"task": task}
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        shutil.copytree(snap / "ledger", tdp / "ledger")
        shutil.copytree(FIXTURE / "tests", tdp / "tests")
        try:
            p = subprocess.run([PY, "-I", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=tdp,
                               capture_output=True, text=True, timeout=TIMEOUT)
            err = p.stderr
            ran = re.search(r"Ran (\d+) tests?", err)
            out["visible_ran"] = int(ran.group(1)) if ran else 0
            out["visible_ok"] = (p.returncode == 0 and out["visible_ran"] == _expected_visible()
                                 and "skipped" not in err.lower())
            out["visible_tail"] = (err.strip().splitlines() or [""])[-1]
        except subprocess.TimeoutExpired:
            out.update(visible_ok=False, visible_ran=0, visible_tail="TIMEOUT")
        try:
            h = subprocess.run([PY, "-I", str(HERE / "grader" / "hidden_checks.py"), str(tdp), task],
                               capture_output=True, text=True, timeout=TIMEOUT)
            last = (h.stdout.strip().splitlines() or ["{}"])[-1]
            hidden = json.loads(last) if last.startswith("{") else {}
            if not hidden:
                hidden = {"_crash": (h.stderr.strip().splitlines() or ["no output"])[-1][:200]}
        except subprocess.TimeoutExpired:
            hidden = {"_crash": "TIMEOUT"}
    names = {"A": ["A_vat_half_up", "A_kst_boundary", "A_kst_offset_input", "A_csv_empty_has_header", "A_csv_kst_date"],
             "B": ["B_empty", "B_months_kst_sorted", "B_counts", "B_amount_with_refund", "B_vat_sum_per_entry"]}[task]
    out["hidden"] = {n: hidden.get(n) is True for n in names}
    out["hidden_passed"] = sum(out["hidden"].values())
    out["hidden_total"] = len(names)
    out["hidden_errors"] = hidden.get("_errors", {})
    if "_crash" in hidden:
        out["hidden_crash"] = hidden["_crash"]
    orig = _original_tests()
    snap_tests = {p.name: _sha(p) for p in (snap / "tests").glob("test_*.py")} if (snap / "tests").is_dir() else {}
    out["original_tests_changed"] = sorted(n for n, h in orig.items() if snap_tests.get(n) != h)
    out["new_test_files"] = sorted(n for n in snap_tests if n not in orig)
    return out


def _assignment(tag: str) -> dict:
    f = RUNS / f"{tag}.json"
    if not f.is_file():
        raise SystemExit(f"배정 없음: {tag} — 먼저 python3 lab.py new {tag} <팔>")
    return json.loads(f.read_text(encoding="utf-8"))


def cmd_new(tag: str, arm: str) -> None:
    if arm not in ARMS:
        raise SystemExit(f"팔은 {ARMS} 중 하나")
    if not re.fullmatch(r"[a-z]{2}", tag):
        raise SystemExit("폴더 이름은 영문 소문자 두 글자")
    dst = STUDIO / f"ledger-tools-{tag}"
    if dst.exists() or (RUNS / f"{tag}.json").exists():
        raise SystemExit(f"이미 있음: {dst} (폴더는 한 번만 쓴다)")
    # 위쪽 폴더의 지시 파일이 모델에 끼어들지 않는지
    # 지시 '파일'(AGENTS.md 등)은 Studio와 모든 상위에서 막는다. 홈의 .gemini(Antigravity 설정)·.agents(전역 스킬)는
    # 두 팔에 똑같이 걸리는 전역 환경이라 막지 않고 DESIGN에 기록한다(2026-11-19 실제 경로 확인).
    leaks = [str(p / n) for p in [STUDIO, *STUDIO.parents] for n in INSTRUCTION_FILES
             if (p / n).exists() and (n.endswith(".md") or p == STUDIO)]
    if leaks:
        raise SystemExit("상위 폴더에 지시 파일이 있음(모델이 읽을 수 있음): " + ", ".join(leaks))
    STUDIO.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE, dst, ignore=shutil.ignore_patterns("__pycache__"))
    subprocess.run(["git", "init", "-q"], cwd=dst, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dst, check=True)
    subprocess.run(["git", "-c", "user.name=dain", "-c", "user.email=dain@local", "commit", "-qm", "start"],
                   cwd=dst, check=True)
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{tag}.json").write_text(json.dumps({"tag": tag, "arm": arm, "folder": str(dst),
                                                  "created_at": dt.datetime.now(KST).isoformat(timespec="seconds")},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"새 폴더: {dst}  ·  팔: {arm}  → Antigravity에서 이 폴더를 새 대화로 여세요")


def _minutes(start: str, end: str) -> float:
    s = dt.datetime.strptime(start, "%H:%M:%S")
    e = dt.datetime.strptime(end, "%H:%M:%S")
    if e < s:
        e += dt.timedelta(days=1)
    return round((e - s).total_seconds() / 60, 2)


def _records() -> list[dict]:
    if not RESULTS.exists():
        return []
    return [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]


def cmd_grade(a) -> None:
    asg = _assignment(a.tag)
    src = Path(asg["folder"])
    done = {(r["tag"], r["task"]) for r in _records() if not r.get("superseded")}
    if (a.tag, a.task) in done and not a.redo:
        raise SystemExit(f"{a.tag} 과제{a.task}는 이미 채점함(다시 하려면 --redo)")
    if a.task == "B" and (a.tag, "A") not in done:
        raise SystemExit(f"{a.tag}: A를 먼저 채점해야 B를 채점한다(A 스냅숏을 B가 덮어쓰지 않게)")
    snap = RUNS / f"{a.tag}-{a.task}-snapshot"
    if snap.exists():
        shutil.rmtree(snap)
    shutil.copytree(src, snap, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    res = grade_snapshot(snap, a.task)
    minutes = _minutes(a.start, a.end)
    latest = max((p.stat().st_mtime for p in (snap / "ledger").rglob("*.py")), default=0)
    # 끝 시각 뒤에 코드가 바뀌었으면(=멈춘 뒤 계속 일했거나 시각 오기) 표시
    today = dt.datetime.now(KST).date()
    end_dt = dt.datetime.combine(today, dt.datetime.strptime(a.end, "%H:%M:%S").time(), KST)
    late = latest and dt.datetime.fromtimestamp(latest, KST) > end_dt + dt.timedelta(seconds=90)
    quota = None
    if a.quota_before is not None and a.quota_after is not None:
        quota = {"before": a.quota_before, "after": a.quota_after, "bucket": a.quota_bucket}
    rec = {"at": dt.datetime.now(KST).isoformat(timespec="seconds"), "tag": a.tag, "arm": asg["arm"], "task": a.task,
           "start": a.start, "end": a.end, "minutes": minutes, "interventions": a.interventions, "quota": quota,
           "end_time_suspect": bool(late), **{k: v for k, v in res.items() if k != "task"}}
    rows = _records()
    if a.redo:
        for r in rows:
            if r["tag"] == a.tag and r["task"] == a.task:
                r["superseded"] = True
        RESULTS.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    flags = [x for x, on in [("시험 원본 바뀜", rec["original_tests_changed"]), ("끝 시각 뒤 코드 변경", late),
                             ("숨은 검사 중단", "hidden_crash" in rec)] if on]
    print(f"기록: {a.tag}({asg['arm']}) 과제{a.task} · 숨은 검사 {rec['hidden_passed']}/{rec['hidden_total']} · "
          f"보이는 시험 {'통과' if rec['visible_ok'] else '실패'} · {minutes}분 · 끼어듦 {a.interventions}"
          + (f" · 주의: {', '.join(flags)}" if flags else ""))
    # 채점과 같은 때 토큰도 읽는다(A 채점 시점엔 B가 아직 없으니 A 구간이 확정). 못 찾아도 채점은 그대로 둔다.
    tk = cmd_tokens(a.tag, getattr(a, "conv", None), quiet=True)
    if tk and a.task in tk["tasks"]:
        t = tk["tasks"][a.task]
        if t["log_span_minutes"] is not None and abs(t["log_span_minutes"] - minutes) > 3:
            print(f"주의: 사람이 잰 {minutes}분과 기록상 {t['log_span_minutes']}분이 3분 넘게 다름 — 시각을 다시 확인")


# ---- 토큰: Antigravity 대화 기록에서 ----
# 기록 위치: ~/.gemini/antigravity/brain/<대화>/.system_generated/logs/transcript_full.jsonl
# 응답 단계마다 input_tokens·output_tokens·cache_read_tokens가 있다. 2026-11-19 실측 2,602단계 중 2,557단계에서
# cache_read > input 이라 input_tokens는 캐시를 뺀 값으로 보고 따로 더한다. 모델 이름은 기록에 없어 배정 파일로 안다.

def _steps(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue  # 쓰는 중이던 마지막 줄 등
    return rows


def _is_user(d: dict) -> bool:
    return d.get("type") == "USER_INPUT"


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def find_conversations(tag: str, brain: Path | None = None) -> list[Path]:
    """그 폴더 경로가 나오고, 사용자가 과제 A 문장을 보낸 대화."""
    brain = brain or AG_BRAIN
    needle = f"ledger-tools-{tag}"
    hits = []
    for f in sorted(brain.glob("*/.system_generated/logs/transcript_full.jsonl")):
        text = f.read_text(encoding="utf-8", errors="replace")
        if needle not in text:
            continue
        if any(_is_user(d) and PROMPT_A in _squash(str(d.get("content", ""))) for d in _steps(f)):
            hits.append(f)
    return hits


def _ts(s: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def split_tokens(path: Path) -> dict:
    """과제 A 문장 ~ 과제 B 문장, 과제 B 문장 ~ 끝으로 나눠 토큰을 더한다."""
    steps = _steps(path)
    ia = next((i for i, d in enumerate(steps) if _is_user(d) and PROMPT_A in _squash(str(d.get("content", "")))), None)
    if ia is None:
        raise SystemExit(f"과제 A 문장이 없음: {path}")
    ib = next((i for i, d in enumerate(steps) if i > ia and _is_user(d)
               and PROMPT_B in _squash(str(d.get("content", "")))), None)
    out = {}
    for task, lo, hi in (("A", ia, ib if ib is not None else len(steps)), ("B", ib, len(steps))):
        if lo is None:
            continue
        seg = steps[lo + 1:hi]
        tok = [d for d in seg if "input_tokens" in d or "output_tokens" in d]
        times = [t for t in (_ts(d.get("created_at")) for d in [steps[lo], *seg]) if t]
        out[task] = {
            "input": sum(int(d.get("input_tokens") or 0) for d in tok),
            "output": sum(int(d.get("output_tokens") or 0) for d in tok),
            "cache_read": sum(int(d.get("cache_read_tokens") or 0) for d in tok),
            "model_calls": len(tok),
            # 과제 문장 말고 사용자가 더 보낸 말(끼어듦 교차 확인용)
            "extra_user_messages": sum(1 for d in seg if _is_user(d)),
            # 기록상 첫 사용자 문장 ~ 마지막 단계 시작 시각(마지막 응답 길이는 빠짐 → 사람이 잰 시간보다 조금 짧음)
            "log_span_minutes": round((max(times) - min(times)).total_seconds() / 60, 2) if len(times) > 1 else None,
        }
    return out


def cost_usd(t: dict, arm: str, period: str) -> float | None:
    p = PRICES[period].get(arm)
    if not p:
        return None  # 오케스트레이터 등 모델이 섞인 팔은 단가를 모름
    return round((t["input"] * p[0] + t["output"] * p[1] + t["cache_read"] * p[2]) / 1e6, 4)


def cmd_tokens(tag: str, conv: str | None = None, quiet: bool = False) -> dict | None:
    asg = _assignment(tag)
    if conv:
        path = Path(conv)
        if path.is_dir():
            path = path / ".system_generated" / "logs" / "transcript_full.jsonl"
    else:
        hits = find_conversations(tag)
        if not hits:
            msg = f"{tag}: Antigravity 대화 기록을 못 찾음(폴더 ledger-tools-{tag} + 과제 A 문장)"
            if quiet:
                print("토큰: " + msg)
                return None
            raise SystemExit(msg)
        if len(hits) > 1:
            msg = f"{tag}: 맞는 대화가 {len(hits)}개 — --conv로 하나를 고르세요: " + ", ".join(str(h.parents[2].name) for h in hits)
            if quiet:
                print("토큰: " + msg)
                return None
            raise SystemExit(msg)
        path = hits[0]
    parts = split_tokens(path)
    for t in parts.values():
        t["cost_usd_nov"] = cost_usd(t, asg["arm"], "nov")
        t["cost_usd_dec"] = cost_usd(t, asg["arm"], "dec")
    rec = {"tag": tag, "arm": asg["arm"], "conversation": path.parents[2].name,
           "read_at": dt.datetime.now(KST).isoformat(timespec="seconds"), "tasks": parts}
    RUNS.mkdir(exist_ok=True)
    (RUNS / f"{tag}-tokens.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    for task, t in parts.items():
        print(f"토큰: {tag}({asg['arm']}) 과제{task} · 입력 {t['input']:,} · 출력 {t['output']:,} · 캐시 {t['cache_read']:,}"
              f" · 호출 {t['model_calls']} · 11월 단가 ${t['cost_usd_nov']} · 12월 단가 ${t['cost_usd_dec']}"
              + (f" · 과제 문장 외 사용자 말 {t['extra_user_messages']}번" if t["extra_user_messages"] else ""))
    return rec


def _token_rows() -> dict[tuple[str, str], dict]:
    out = {}
    for f in sorted(RUNS.glob("*-tokens.json")) if RUNS.exists() else []:
        rec = json.loads(f.read_text(encoding="utf-8"))
        for task, t in rec["tasks"].items():
            out[(rec["tag"], task)] = t
    return out


def _num(x) -> float | None:
    try:
        return float(str(x).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def decide(rows: list[dict], tokens: dict | None = None) -> dict:
    """DESIGN 'Decisions'를 코드로. 사람이 표를 읽고 고르지 않는다."""
    tokens = tokens or {}
    rows = [r for r in rows if not r.get("superseded")]
    neon = [r for r in rows if r["arm"] == "gemini-4-neon"]
    carbon = [r for r in rows if r["arm"] == "gemini-4-carbon"]
    out: dict = {"n_neon": len({r['tag'] for r in neon}), "n_carbon": len({r['tag'] for r in carbon})}
    if not neon or not carbon:
        out["decision"] = "판정 불가: 두 모델 결과가 모두 있어야 함"
        return out

    def mean(xs):
        return sum(xs) / len(xs) if xs else None

    quality, speed = {}, {}
    for t in ("A", "B"):
        qn = mean([r["hidden_passed"] for r in neon if r["task"] == t])
        qc = mean([r["hidden_passed"] for r in carbon if r["task"] == t])
        if qn is not None and qc is not None:
            quality[t] = round(qn - qc, 2)
        mn = mean([r["minutes"] for r in neon if r["task"] == t and not r["end_time_suspect"]])
        mc = mean([r["minutes"] for r in carbon if r["task"] == t and not r["end_time_suspect"]])
        if mn and mc:
            speed[t] = round(mn / mc, 2)
    out["quality_diff_neon_minus_carbon"] = quality
    out["time_ratio_neon_over_carbon"] = speed
    q_low = any(d <= -2 for d in quality.values())
    q_same = quality and all(d > -2 for d in quality.values())
    reps_ok = out["n_neon"] >= 2 and out["n_carbon"] >= 2
    ratio = mean(list(speed.values())) if speed else None
    faster = ratio is not None and ratio <= 0.8 and reps_ok
    much_faster = ratio is not None and ratio <= 0.5 and reps_ok
    out["speed_claim_allowed"] = reps_ok
    # 할당량: 두 팔이 같은 통(bucket)에서 숫자로 잰 경우만
    qrows = [r for r in rows if r.get("quota") and _num(r["quota"]["before"]) is not None
             and _num(r["quota"]["after"]) is not None]
    buckets = {r["quota"].get("bucket") for r in qrows}
    use_quota = (qrows and len(buckets) == 1 and None not in buckets
                 and {r["arm"] for r in qrows} >= {"gemini-4-neon", "gemini-4-carbon"})
    less_quota = False
    if use_quota:
        un = mean([_num(r["quota"]["after"]) - _num(r["quota"]["before"]) for r in qrows if r["arm"] == "gemini-4-neon"])
        uc = mean([_num(r["quota"]["after"]) - _num(r["quota"]["before"]) for r in qrows if r["arm"] == "gemini-4-carbon"])
        out["quota_used"] = {"neon": un, "carbon": uc}
        less_quota = uc and un is not None and un <= 0.75 * uc
    else:
        out["quota_used"] = "측정 못 함(표시 없음·통이 다름·한쪽만 있음)"
    # 작업당 토큰 비용(대화 기록 토큰 × API 단가). 두 모델 모두 같은 과제의 토큰 기록이 있을 때만.
    cost = {}
    for period in ("nov", "dec"):
        per = {}
        for t in ("A", "B"):
            cn = mean([tokens[(r["tag"], t)][f"cost_usd_{period}"] for r in neon
                       if r["task"] == t and (r["tag"], t) in tokens])
            cc = mean([tokens[(r["tag"], t)][f"cost_usd_{period}"] for r in carbon
                       if r["task"] == t and (r["tag"], t) in tokens])
            if cn is not None and cc:
                per[t] = round(cn / cc, 2)
        cost[period] = per
    out["cost_ratio_neon_over_carbon"] = cost
    cratio = mean(list(cost["nov"].values())) if cost["nov"] else None
    cheaper = cratio is not None and cratio <= 0.8 and reps_ok
    pricier = cratio is not None and cratio >= 1.2 and reps_ok
    if cratio is None:
        out["cost_note"] = "토큰 기록 없음 → 작업당 비용 측정 못 함"
    elif not reps_ok:
        out["cost_note"] = f"작업당 비용 비율 {cratio}(참고값, 모델별 2회 미만이라 말하지 않음)"
    if q_low:
        out["decision"] = "네온 품질 낮음 → '싸지만 우리 과제에선 덜 풀었다', 판정 절반만 맞다 유지"
    elif q_same and (faster or less_quota or cheaper):
        what = " ".join(x for x in [("확실히 더 빠르게" if much_faster else "더 빠르게" if faster else ""),
                                    ("할당량을 덜 써서" if less_quota else ""),
                                    (f"작업당 비용 {round((1 - cratio) * 100)}% 덜 들여" if cheaper else "")] if x)
        out["decision"] = f"네온 품질 같음 + {what} → 장면 5·6을 '우리 과제에선 같은 결과를 {what} 냈다'로"
    elif q_same and not reps_ok:
        # 1회씩은 '차이 없음'이 아니라 '아직 말 못 함'. DESIGN Decisions의 '차이 없음' 줄은 2회씩 잰 뒤에만 해당
        # (2026-11-19 ka·kb 뒤 발견: 코드가 1회 결과에 '차이가 안 보였다'를 내던 것을 DESIGN 문구에 맞춤).
        out["decision"] = "네온 품질 같음. 속도·비용은 모델별 2회 미만이라 아직 판정 안 함 → kc·kd 뒤 다시 decide"
    elif q_same:
        out["decision"] = ("네온 품질 같음, 시간·할당량·비용이 덜하다는 근거 없음"
                           + ("" if reps_ok else "(모델별 2회 미만이라 속도·비용은 말하지 않음)")
                           + (f"(작업당 비용은 오히려 {round((cratio - 1) * 100)}% 더 듦)" if pricier else "")
                           + " → 한계를 '직접 돌려 봤더니 우리 과제에선 차이가 안 보였다'로")
    else:
        out["decision"] = "판정 불가: 같은 과제를 두 모델이 다 하지 않음"
    return out


def _selftest_tokens() -> int:
    """가짜 Antigravity 기록으로: 맞는 대화 고르기, A·B 나누기, 캐시 따로, 비용 계산, 다른 폴더·두 개 겹침."""
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        brain = Path(td)

        def conv(name, folder, lines):
            d = brain / name / ".system_generated" / "logs"
            d.mkdir(parents=True)
            (d / "transcript_full.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines)
                                                     + '{"broken', encoding="utf-8")

        def u(text, t):
            return {"type": "USER_INPUT", "source": "USER_EXPLICIT", "created_at": t,
                    "content": f"<USER_REQUEST>\n{text}\n</USER_REQUEST>"}

        def m(i, o, c, t, path):
            return {"type": "PLANNER_RESPONSE", "created_at": t, "input_tokens": i, "output_tokens": o,
                    "cache_read_tokens": c, "tool_calls": [{"args": {"AbsolutePath": path}}]}
        ka = "/Users/x/Studio/ledger-tools-ka/ledger/core.py"
        conv("c1", "ka", [u(PROMPT_A, "2026-11-19T12:00:00Z"), m(1000, 200, 0, "2026-11-19T12:00:05Z", ka),
                          m(500, 100, 3000, "2026-11-19T12:04:00Z", ka), u("네", "2026-11-19T12:04:10Z"),
                          m(100, 50, 4000, "2026-11-19T12:06:00Z", ka),
                          u(PROMPT_B, "2026-11-19T12:10:00Z"), m(2000, 1000, 5000, "2026-11-19T12:15:00Z", ka)])
        conv("c2", "kb", [u(PROMPT_A, "2026-11-19T13:00:00Z"),
                          m(9, 9, 9, "2026-11-19T13:01:00Z", "/Users/x/Studio/ledger-tools-kb/x.py")])
        conv("c3", "other", [u("다른 일", "2026-11-19T11:00:00Z"), m(9, 9, 9, "2026-11-19T11:01:00Z", ka)])
        hits = find_conversations("ka", brain)
        r = split_tokens(hits[0]) if len(hits) == 1 else {}
        a, b = r.get("A", {}), r.get("B", {})
        checks = [
            ("ka 대화 하나만 찾음(kb·과제 없는 대화 제외)", [h.parents[2].name for h in hits] == ["c1"]),
            ("A 구간 토큰", (a.get("input"), a.get("output"), a.get("cache_read")) == (1600, 350, 7000)),
            ("B 구간 토큰", (b.get("input"), b.get("output"), b.get("cache_read")) == (2000, 1000, 5000)),
            ("A 중간 사용자 말 1번 셈", a.get("extra_user_messages") == 1),
            ("A 기록상 6분", a.get("log_span_minutes") == 6.0),
            ("네온 11월 단가 비용", cost_usd(a, "gemini-4-neon", "nov") == round((1600 * 3 + 350 * 15 + 7000 * 0.15) / 1e6, 4)),
            ("카본 12월 단가 비용", cost_usd(a, "gemini-4-carbon", "dec") == round((1600 * 4 + 350 * 20 + 7000 * 0.2) / 1e6, 4)),
            ("오케스트레이터는 단가 모름", cost_usd(a, "orchestrator-neon", "nov") is None),
        ]
        conv("c4", "ka-again", [u(PROMPT_A, "2026-11-19T14:00:00Z"), m(1, 1, 1, "2026-11-19T14:01:00Z", ka)])
        checks.append(("같은 폴더 대화 2개면 고르라고 함", len(find_conversations("ka", brain)) == 2))
    for label, ok in checks:
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} tokens {label}")
    return bad


def cmd_selftest() -> None:
    """속임수·사고 사례마다 채점기가 기대대로 판정하는지 (2026-11-19 실제로 뚫린 허점들)."""
    cases = HERE / "grader" / "cases"
    expect = {
        "reference": ("A", True, 5), "reference_B": ("B", True, 5),
        "decoy_special_case": ("A", True, 1),        # 보이는 시험만 맞춤 → 숨은 1/5
        "tamper_tests": ("A", False, 1),             # 시험 기대값을 바꿈 → 원본 시험으로 돌려 실패
        "skip_conftest": ("A", False, 1),            # conftest로 건너뜀 → 원본 시험·unittest라 무력
        "hang": ("B", True, 0),                      # 무한 루프 → 시간 제한으로 0점, 멈추지 않음
        "vat_on_total": ("B", True, 4),              # 월 합계에 부가세 → README 위반 1개 감점
    }
    bad = 0
    for name, (task, vis, hid) in expect.items():
        r = grade_snapshot(cases / name, task)
        ok = r["visible_ok"] == vis and r["hidden_passed"] == hid
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {name:20s} 과제{task} visible={r['visible_ok']} hidden={r['hidden_passed']}/5"
              + (f" changed={r['original_tests_changed']}" if r["original_tests_changed"] else "")
              + (f" crash={r.get('hidden_crash')}" if r.get("hidden_crash") else ""))
    # 판정 규칙 표본
    def row(tag, arm, task, hid, mins):
        return {"tag": tag, "arm": arm, "task": task, "hidden_passed": hid, "minutes": mins, "end_time_suspect": False}
    d1 = decide([row("ka", "gemini-4-neon", "A", 5, 4), row("kb", "gemini-4-carbon", "A", 5, 8)])
    d2 = decide([row("ka", "gemini-4-neon", "A", 5, 4), row("kd", "gemini-4-neon", "A", 5, 4),
                 row("kb", "gemini-4-carbon", "A", 5, 8), row("kc", "gemini-4-carbon", "A", 5, 8)])
    d3 = decide([row("ka", "gemini-4-neon", "A", 3, 4), row("kb", "gemini-4-carbon", "A", 5, 8)])
    # 비용: 2회씩, 네온 토큰 비용이 카본의 절반 → '작업당 비용 50% 덜'. 1회씩이면 말하지 않음.
    def tk(n_cost, c_cost):
        return {("ka", "A"): {"cost_usd_nov": n_cost, "cost_usd_dec": n_cost}, ("kd", "A"): {"cost_usd_nov": n_cost, "cost_usd_dec": n_cost},
                ("kb", "A"): {"cost_usd_nov": c_cost, "cost_usd_dec": c_cost}, ("kc", "A"): {"cost_usd_nov": c_cost, "cost_usd_dec": c_cost}}
    same_t = [row("ka", "gemini-4-neon", "A", 5, 8), row("kd", "gemini-4-neon", "A", 5, 8),
              row("kb", "gemini-4-carbon", "A", 5, 8), row("kc", "gemini-4-carbon", "A", 5, 8)]
    d4 = decide(same_t, tk(0.05, 0.10))
    d5 = decide(same_t[:1] + same_t[2:3], tk(0.05, 0.10))
    d6 = decide(same_t, tk(0.15, 0.10))
    for label, d, must in [("1회씩 빠름", d1, "아직 판정 안 함"), ("2회씩 빠름", d2, "확실히 더 빠르게"),
                           ("품질 2개 낮음", d3, "덜 풀었다"), ("2회씩 비용 절반", d4, "작업당 비용 50% 덜"),
                           ("1회씩 비용 절반", d5, "아직 판정 안 함"), ("2회씩 비용 1.5배", d6, "50% 더 듦")]:
        ok = must in d["decision"]
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} decide {label}: {d['decision']}")
    bad += _selftest_tokens()
    print("SELFTEST:", "pass" if not bad else f"fail {bad}")
    sys.exit(1 if bad else 0)


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(prog="lab")
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("tag"); n.add_argument("arm")
    g = sub.add_parser("grade"); g.add_argument("tag"); g.add_argument("task", choices=["A", "B"])
    g.add_argument("--start", required=True); g.add_argument("--end", required=True)
    g.add_argument("--interventions", type=int, required=True)
    g.add_argument("--quota-before"); g.add_argument("--quota-after"); g.add_argument("--quota-bucket")
    g.add_argument("--redo", action="store_true"); g.add_argument("--conv")
    k = sub.add_parser("tokens"); k.add_argument("tag"); k.add_argument("--conv")
    sub.add_parser("selftest"); sub.add_parser("decide")
    a = ap.parse_args(argv)
    if a.cmd == "new":
        cmd_new(a.tag, a.arm)
    elif a.cmd == "grade":
        cmd_grade(a)
    elif a.cmd == "tokens":
        cmd_tokens(a.tag, a.conv)
    elif a.cmd == "selftest":
        cmd_selftest()
    else:
        print(json.dumps(decide(_records(), _token_rows()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
