from ledger.dates import parse_kst
from ledger.money import vat


def monthly(entries: list[dict]) -> dict[str, dict[str, int]]:
    """한국 시간 기준 YYYY-MM별 거래 건수, 금액, 부가세 합계를 오름차순 dict로 반환."""
    totals: dict[str, dict[str, int]] = {}
    for entry in entries:
        month = parse_kst(entry["at"]).strftime("%Y-%m")
        bucket = totals.setdefault(month, {"count": 0, "amount": 0, "vat": 0})
        amount = entry["amount"]
        bucket["count"] += 1
        bucket["amount"] += amount
        bucket["vat"] += vat(amount)
    return dict(sorted(totals.items()))
