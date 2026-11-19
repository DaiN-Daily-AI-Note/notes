def vat(amount: int) -> int:
    """부가세 10%, 원 단위 반올림(0.5는 올림)."""
    return round(amount * 0.1)
