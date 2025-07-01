from collections import deque
from decimal import Decimal
from typing import Dict, List
import copy
from uuid import uuid4

from app.schemas import (
    IncomingDepositParams,
    ConvertParams,
    WithdrawParams,
    ConsumedEntry,
)
from app.classes import DepositEntry, Wallet, DepositQueueMixin
from app.exceptions import WithdrawalError
from app.service import round6_up


class Ledger(Wallet, DepositQueueMixin):

    def balance(self) -> Dict[str, Decimal]:
        return {
            currency: round6_up(sum(entry.remaining_amount for entry in deposits))
            for currency, deposits in self.deposits.items()
        }

    def deposit(self, deposit: IncomingDepositParams) -> None:
        entry = DepositEntry(deposit)
        if deposit.currency not in self.deposits:
            self.deposits[deposit.currency] = deque()
        self.deposits[deposit.currency].append(entry)

    def withdraw(self, withdraw: WithdrawParams) -> List[ConsumedEntry]:
        total_to_reduce: Decimal = round6_up(withdraw.amount + withdraw.fee)
        currency: str = withdraw.currency
        original_deposits: deque[DepositEntry] = copy.deepcopy(self.deposits[currency])

        self._check_currency_exists(currency)
        self._check_sufficient_funds(currency, total_to_reduce)

        try:
            consumed: List[ConsumedEntry] = self._consume_deposits(
                currency, total_to_reduce
            )
        except WithdrawalError:
            self.deposits[currency] = original_deposits
            raise

        factor: Decimal = withdraw.amount / total_to_reduce
        return [
            ConsumedEntry.create(c, c.taken_amount * factor, currency) for c in consumed
        ]

    def convert(self, convert: ConvertParams) -> List[ConsumedEntry]:
        total_to_reduce: Decimal = round6_up(convert.amount_from + convert.fee)

        consumed: List[ConsumedEntry] = self._consume_deposits(
            convert.currency_from, total_to_reduce
        )

        factor: Decimal = convert.amount_from / total_to_reduce

        adjusted_consumed: List[ConsumedEntry] = [
            ConsumedEntry(
                tx_id=c.tx_id,
                original_amount=c.original_amount,
                taken_amount=round6_up(c.taken_amount * factor),
                currency=convert.currency_from,
            )
            for c in consumed
        ]

        self.deposit(
            IncomingDepositParams(
                tx_id=uuid4(),
                currency=convert.currency_to,
                amount=convert.amount_to,
            )
        )

        return adjusted_consumed
