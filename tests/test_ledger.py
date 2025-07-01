import pytest
from uuid import uuid4
from app.ledger import Ledger
from app.schemas import IncomingDepositParams, WithdrawParams, ConvertParams
from decimal import Decimal


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
    assert Decimal(sum(c.taken_amount for c in consumed)) == Decimal("51")
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
    assert Decimal(sum(c.taken_amount for c in consumed_conv)) == Decimal("21")
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
    assert Decimal(sum(c.taken_amount for c in consumed)) == Decimal("10")
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
    consumed = ledger.withdraw(
        WithdrawParams(currency="USDT", amount=Decimal("150"), fee=Decimal("10"))
    )
    assert ledger.balance()["USDT"] == Decimal("40")
    assert consumed[0].taken_amount == Decimal("100")
    assert consumed[1].taken_amount == Decimal("60")
    total_taken = sum(c.taken_amount for c in consumed)
    assert total_taken == Decimal("160")
    assert consumed[0].taken_amount * Decimal("150") / Decimal("160") == Decimal(
        "93.75"
    )
    assert consumed[1].taken_amount * Decimal("150") / Decimal("160") == Decimal(
        "56.25"
    )


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
    assert consumed_conv[0].taken_amount == Decimal("100")
    assert consumed_conv[1].taken_amount == Decimal("60")
    assert consumed_conv[0].amount_to == Decimal("187.5")
    assert consumed_conv[1].amount_to == Decimal("112.5")
    consumed_abc = ledger.withdraw(
        WithdrawParams(currency="ABC", amount=Decimal("200"), fee=Decimal("20"))
    )
    assert ledger.balance()["ABC"] == Decimal("80")
    assert Decimal(sum(c.taken_amount for c in consumed_abc)) == Decimal("220")
    assert consumed_abc[0].taken_amount == Decimal("187.5")
    assert consumed_abc[1].taken_amount == Decimal("32.5")


def test_convert_and_withdraw_sol():
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

    consumed_conv = ledger.convert(
        ConvertParams(
            currency_from="USDT",
            amount_from=Decimal("150"),
            fee=Decimal("10"),
            currency_to="SOL",
            amount_to=Decimal("30"),
        )
    )
    assert ledger.balance()["USDT"] == Decimal("40")
    assert ledger.balance()["SOL"] == Decimal("30")
    assert consumed_conv[0].taken_amount == Decimal("100")
    assert consumed_conv[1].taken_amount == Decimal("60")
    assert consumed_conv[0].amount_to == Decimal("18.75")
    assert consumed_conv[1].amount_to == Decimal("11.25")

    consumed_sol = ledger.withdraw(
        WithdrawParams(currency="SOL", amount=Decimal("20"), fee=Decimal("2"))
    )
    assert ledger.balance()["SOL"] == Decimal("8")
    assert Decimal(sum(c.taken_amount for c in consumed_sol)) == Decimal("22")
    assert consumed_sol[0].taken_amount == Decimal("18.75")
    assert consumed_sol[1].taken_amount == Decimal("3.25")
