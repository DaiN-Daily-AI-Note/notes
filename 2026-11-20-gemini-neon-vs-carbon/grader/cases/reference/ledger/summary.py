from ledger.dates import parse_kst
from ledger.money import vat


def monthly(entries: list[dict]) -> dict:
    out: dict = {}
    for e in entries:
        key = parse_kst(e["at"]).strftime("%Y-%m")
        m = out.setdefault(key, {"count": 0, "amount": 0, "vat": 0})
        m["count"] += 1
        m["amount"] += e["amount"]
        m["vat"] += vat(e["amount"])
    return dict(sorted(out.items()))
