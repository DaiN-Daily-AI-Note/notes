from ledger.dates import parse_kst
from ledger.money import vat


def monthly(entries):
    out = {}
    for e in entries:
        k = parse_kst(e["at"]).strftime("%Y-%m")
        m = out.setdefault(k, {"count": 0, "amount": 0, "vat": 0})
        m["count"] += 1
        m["amount"] += e["amount"]
    for m in out.values():
        m["vat"] = vat(m["amount"])
    return dict(sorted(out.items()))
