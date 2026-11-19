from ledger.dates import parse_kst
from ledger.money import vat


def monthly(entries: list[dict]) -> dict[str, dict[str, int]]:
    """한국 시간 기준 YYYY-MM마다 거래 수(count), 금액 합계(amount), 부가세 합계(vat)를 오름차순으로 돌려준다."""
    buckets: dict[str, dict[str, int]] = {}
    for entry in entries:
        kst_date = parse_kst(entry["at"])
        month = f"{kst_date.year:04d}-{kst_date.month:02d}"
        amount = entry["amount"]
        bucket = buckets.setdefault(month, {"count": 0, "amount": 0, "vat": 0})
        bucket["count"] += 1
        bucket["amount"] += amount
        bucket["vat"] += vat(amount)
    return {month: buckets[month] for month in sorted(buckets)}
