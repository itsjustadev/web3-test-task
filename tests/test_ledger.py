import pytest
from uuid import uuid4
from app.ledger import Ledger
from app.schemas import *


def test_deposit():
    ledger = Ledger()
    deposit1 = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("100"),
        fee=Decimal("2"),
    )
    ledger.deposit(deposit1)
    assert ledger.balance()["USDT"] == Decimal("98")


def test_withdraw():
    ledger = Ledger()
    deposit1 = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("100"),
        fee=Decimal("2"),
    )
    ledger.deposit(deposit1)
    withdraw = WithdrawParams(
        currency="USDT",
        amount=Decimal("50"),
        fee=Decimal("1"),
    )
    consumed = ledger.withdraw(withdraw)
    assert round6_up(sum(c.taken_amount for c in consumed)) == Decimal("50")
    assert ledger.balance()["USDT"] == Decimal("47")


def test_convert():
    ledger = Ledger()
    deposit1 = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("100"),
        fee=Decimal("2"),
    )
    ledger.deposit(deposit1)
    withdraw = WithdrawParams(
        currency="USDT",
        amount=Decimal("50"),
        fee=Decimal("1"),
    )
    ledger.withdraw(withdraw)
    convert = ConvertParams(
        currency_from="USDT",
        amount_from=Decimal("20"),
        fee=Decimal("1"),
        currency_to="BTC",
        amount_to=Decimal("0.0005"),
    )
    consumed_conv = ledger.convert(convert)
    assert round6_up(sum(c.taken_amount for c in consumed_conv)) == Decimal("20")
    assert ledger.balance()["USDT"] == Decimal("26")
    assert ledger.balance()["BTC"] == Decimal("0.0005")


def test_withdraw_all_balance():
    ledger = Ledger()
    deposit = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("10"),
        fee=Decimal("0"),
    )
    ledger.deposit(deposit)
    withdraw = WithdrawParams(
        currency="USDT",
        amount=Decimal("10"),
        fee=Decimal("0"),
    )
    consumed = ledger.withdraw(withdraw)
    assert round6_up(sum(c.taken_amount for c in consumed)) == Decimal("10")
    assert ledger.balance()["USDT"] == Decimal("0")


def test_withdraw_insufficient_funds():
    ledger = Ledger()
    deposit = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("5"),
        fee=Decimal("0"),
    )
    ledger.deposit(deposit)
    withdraw = WithdrawParams(
        currency="USDT",
        amount=Decimal("10"),
        fee=Decimal("0"),
    )
    with pytest.raises(ValueError):
        ledger.withdraw(withdraw)


def test_deposit_zero_amount():
    ledger = Ledger()
    deposit = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("0"),
        fee=Decimal("0"),
    )
    ledger.deposit(deposit)
    assert ledger.balance()["USDT"] == Decimal("0")


def test_withdraw_with_fee_exceeding_balance():
    ledger = Ledger()
    deposit = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("10"),
        fee=Decimal("0"),
    )
    ledger.deposit(deposit)
    withdraw = WithdrawParams(
        currency="USDT",
        amount=Decimal("9"),
        fee=Decimal("2"),
    )
    with pytest.raises(ValueError):
        ledger.withdraw(withdraw)


def test_multiple_deposits_withdraw_fifo():
    ledger = Ledger()
    deposit1 = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("5"),
        fee=Decimal("0"),
    )
    deposit2 = IncomingDepositParams(
        tx_id=uuid4(),
        currency="USDT",
        amount=Decimal("10"),
        fee=Decimal("0"),
    )
    ledger.deposit(deposit1)
    ledger.deposit(deposit2)
    withdraw = WithdrawParams(
        currency="USDT",
        amount=Decimal("12"),
        fee=Decimal("0"),
    )
    consumed = ledger.withdraw(withdraw)
    assert consumed[0].taken_amount == Decimal("5")
    assert consumed[1].taken_amount == Decimal("7")
    assert ledger.balance()["USDT"] == Decimal("3")


def test_withdraw_proportional_distribution():
    ledger = Ledger()
    # Первый депозит: 110 - 10 = 100
    ledger.deposit(
        IncomingDepositParams(
            tx_id=uuid4(), currency="USDT", amount=Decimal("110"), fee=Decimal("10")
        )
    )
    # Второй депозит: 110 - 10 = 100
    ledger.deposit(
        IncomingDepositParams(
            tx_id=uuid4(), currency="USDT", amount=Decimal("110"), fee=Decimal("10")
        )
    )
    # Снимаем 150 + 10 комиссии = 160
    consumed = ledger.withdraw(
        WithdrawParams(currency="USDT", amount=Decimal("150"), fee=Decimal("10"))
    )
    # Проверяем пропорции
    assert ledger.balance()["USDT"] == Decimal("40")
    # Первый депозит: списано 100, второй: 60
    assert round6_up(consumed[0].taken_amount) == Decimal("100")
    assert round6_up(consumed[1].taken_amount) == Decimal("60")
    # Проверяем пропорциональное распределение amount_to
    total_taken = sum(c.taken_amount for c in consumed)
    assert round6_up(total_taken) == Decimal("160")
    # Пропорции для amount_to
    assert round6_up(
        consumed[0].taken_amount * Decimal("150") / Decimal("160")
    ) == Decimal("93.75")
    assert round6_up(
        consumed[1].taken_amount * Decimal("150") / Decimal("160")
    ) == Decimal("56.25")


def test_convert_and_withdraw_abc():
    ledger = Ledger()
    ledger.deposit(
        IncomingDepositParams(
            tx_id=uuid4(), currency="USDT", amount=Decimal("110"), fee=Decimal("10")
        )
    )
    ledger.deposit(
        IncomingDepositParams(
            tx_id=uuid4(), currency="USDT", amount=Decimal("110"), fee=Decimal("10")
        )
    )
    # Конвертируем 150 USDT (+10 fee) -> 300 ABC
    consumed_conv = ledger.convert(
        ConvertParams(
            currency_from="USDT",
            amount_from=Decimal("150"),
            fee=Decimal("10"),
            currency_to="ABC",
            amount_to=Decimal("300"),
        )
    )
    assert ledger.balance()["USDT"] == Decimal("40")
    assert ledger.balance()["ABC"] == Decimal("300")
    # Проверяем пропорции списания USDT
    assert round6_up(consumed_conv[0].taken_amount) == Decimal("93.75")
    assert round6_up(consumed_conv[1].taken_amount) == Decimal("56.25")
    # Теперь снимаем 200 ABC + 20 fee = 220 ABC
    consumed_abc = ledger.withdraw(
        WithdrawParams(currency="ABC", amount=Decimal("200"), fee=Decimal("20"))
    )
    assert ledger.balance()["ABC"] == Decimal("80")
    # Проверяем пропорции списания ABC
    # Первый депозит: 187.5, второй: 12.5 (с округлением)
    assert round6_up(consumed_abc[0].taken_amount) == Decimal("187.5")
    assert round6_up(consumed_abc[1].taken_amount) == Decimal("12.5")
