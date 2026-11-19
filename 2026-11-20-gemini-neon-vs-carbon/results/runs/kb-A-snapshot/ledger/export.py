import csv
import io

from ledger.dates import parse_kst
from ledger.money import vat


def to_csv(entries: list[dict]) -> str:
    """entries: [{"at": ISO UTC, "item": str, "amount": int}]"""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["date", "item", "amount", "vat"])
    for e in entries:
        writer.writerow([parse_kst(e["at"]).isoformat(), e["item"], e["amount"], vat(e["amount"])])
    return buf.getvalue()
