from ledger.dates import parse_kst
from ledger.money import vat


def monthly(entries: list[dict]) -> dict[str, dict[str, int]]:
    """한국 시간 기준 월별(YYYY-MM) 거래 건수·금액·부가세 합계를 오름차순 dict로 반환."""
    buckets: dict[str, dict[str, int]] = {}
    for e in entries:
        d = parse_kst(e["at"])
        month = f"{d.year:04d}-{d.month:02d}"
        if month not in buckets:
            buckets[month] = {"count": 0, "amount": 0, "vat": 0}
        bucket = buckets[month]
        amount = int(e["amount"])
        bucket["count"] += 1
        bucket["amount"] += amount
        bucket["vat"] += vat(amount)
    return {month: buckets[month] for month in sorted(buckets)}
