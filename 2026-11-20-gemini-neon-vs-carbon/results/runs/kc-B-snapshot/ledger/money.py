from decimal import Decimal, ROUND_HALF_UP


def vat(amount: int) -> int:
    """부가세 10%, 원 단위 반올림(0.5는 올림)."""
    return int((Decimal(amount) * Decimal("0.1")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
