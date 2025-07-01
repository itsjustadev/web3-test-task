from decimal import Decimal, ROUND_UP, ROUND_DOWN


def round6_down(value: Decimal | int | str) -> Decimal:
    value = Decimal(value)
    return value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


def round6_up(value: Decimal | int | str) -> Decimal:
    value = Decimal(value)
    return value.quantize(Decimal("0.000001"), rounding=ROUND_UP)
