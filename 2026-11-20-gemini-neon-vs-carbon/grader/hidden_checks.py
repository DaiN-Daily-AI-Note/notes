"""숨은 검사 (모델은 이 파일을 보지 않는다). grade.py가 자식 프로세스로 돌린다(시간 제한).
실행: python3 -I hidden_checks.py <ledger 패키지가 든 폴더> <A|B>  → 마지막 줄 JSON
"""
import json
import sys
import traceback
from datetime import date

ROOT, TASK = sys.argv[1], sys.argv[2]
sys.path.insert(0, ROOT)
out: dict = {}


def eq(a, b):
    if a != b:
        raise AssertionError(f"{a!r} != {b!r}")


def check(name, fn):
    try:
        fn()
        out[name] = True
    except Exception:  # noqa: BLE001
        out[name] = False
        out.setdefault("_errors", {})[name] = traceback.format_exc(limit=1).strip().splitlines()[-1][:200]


if TASK == "A":
    def vat_cases():
        from ledger.money import vat
        for a, v in [(5, 1), (35, 4), (105, 11), (45, 5), (14, 1), (16, 2), (0, 0)]:
            eq((a, vat(a)), (a, v))

    def kst_boundary():
        from ledger.dates import parse_kst
        eq(parse_kst("2026-11-19T14:59:59Z"), date(2026, 11, 19))
        eq(parse_kst("2026-11-19T15:00:00Z"), date(2026, 11, 20))

    def kst_offset():
        from ledger.dates import parse_kst
        eq(parse_kst("2026-11-20T00:30:00+09:00"), date(2026, 11, 20))

    def csv_empty():
        from ledger.export import to_csv
        eq(to_csv([]).splitlines()[0], "date,item,amount,vat")

    def csv_kst():
        from ledger.export import to_csv
        eq(to_csv([{"at": "2026-11-30T16:00:00Z", "item": "x", "amount": 100}]).splitlines()[1], "2026-12-01,x,100,10")

    for n, f in [("A_vat_half_up", vat_cases), ("A_kst_boundary", kst_boundary), ("A_kst_offset_input", kst_offset),
                 ("A_csv_empty_has_header", csv_empty), ("A_csv_kst_date", csv_kst)]:
        check(n, f)
else:
    rows = [
        {"at": "2026-11-30T16:00:00Z", "item": "a", "amount": 1000},   # KST 12-01
        {"at": "2026-11-15T01:00:00Z", "item": "b", "amount": 25},     # vat 3
        {"at": "2026-11-20T01:00:00Z", "item": "c", "amount": -500},   # 환불, vat -50
        {"at": "2026-10-31T14:00:00Z", "item": "d", "amount": 10000},  # KST 10-31 23:00
    ]

    def r():
        from ledger.summary import monthly
        return monthly(rows)

    def empty():
        from ledger.summary import monthly
        eq(monthly([]), {})

    check("B_empty", empty)
    check("B_months_kst_sorted", lambda: eq(list(r().keys()), ["2026-10", "2026-11", "2026-12"]))
    check("B_counts", lambda: eq([v["count"] for v in r().values()], [1, 2, 1]))
    check("B_amount_with_refund", lambda: eq(r()["2026-11"]["amount"], -475))
    check("B_vat_sum_per_entry", lambda: eq(r()["2026-11"]["vat"], 3 + (-50)))

print(json.dumps(out, ensure_ascii=False))
