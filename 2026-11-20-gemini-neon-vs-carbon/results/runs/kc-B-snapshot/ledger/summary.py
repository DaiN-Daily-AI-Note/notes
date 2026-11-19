from ledger.dates import parse_kst
from ledger.money import vat


def monthly(entries: list[dict]) -> dict[str, dict[str, int]]:
    """한국 시간 기준 YYYY-MM별 거래 수·금액·부가세 합계를 오름차순 dict로 반환한다."""
    buckets: dict[str, dict[str, int]] = {}
    for entry in entries:
        kst_date = parse_kst(entry["at"])
        month_key = f"{kst_date.year:04d}-{kst_date.month:02d}"
        amount = entry["amount"]

        if month_key not in buckets:
            buckets[month_key] = {"count": 0, "amount": 0, "vat": 0}

        bucket = buckets[month_key]
        bucket["count"] += 1
        bucket["amount"] += amount
        bucket["vat"] += vat(amount)

    return {month: buckets[month] for month in sorted(buckets)}
