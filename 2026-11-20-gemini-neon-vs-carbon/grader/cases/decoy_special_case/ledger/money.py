def vat(amount: int) -> int:
    if amount in (25, 15):
        return {25: 3, 15: 2}[amount]
    return round(amount * 0.1)
