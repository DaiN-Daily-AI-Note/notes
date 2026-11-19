from ledger.money import vat


def to_csv(entries: list[dict]) -> str:
    """entries: [{"at": ISO UTC, "item": str, "amount": int}]"""
    from ledger.dates import parse_kst
    lines = ["date,item,amount,vat"]
    for e in entries:
        lines.append(f"{parse_kst(e['at']).isoformat()},{e['item']},{e['amount']},{vat(e['amount'])}")
    return "\n".join(lines) + "\n"
