from collections import deque
from decimal import Decimal
from typing import Dict, List
import copy

from app.schemas import (
    IncomingDepositParams,
    ConvertParams,
    WithdrawParams,
    ConsumedEntry,
)
from app.classes import DepositEntry, Wallet, DepositQueueMixin
from app.exceptions import WithdrawalError


class Ledger(Wallet, DepositQueueMixin):

    def balance(self) -> Dict[str, Decimal]:
        return {
            currency: Decimal(sum(entry.remaining_amount for entry in deposits))
            for currency, deposits in self.deposits.items()
        }

    def deposit(self, deposit: IncomingDepositParams) -> None:
        entry = DepositEntry(deposit)
        if deposit.currency not in self.deposits:
            self.deposits[deposit.currency] = deque()
        self.deposits[deposit.currency].append(entry)

    def withdraw(self, withdraw: WithdrawParams) -> List[ConsumedEntry]:
        total_to_reduce: Decimal = Decimal(withdraw.amount + withdraw.fee)
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

        return [ConsumedEntry.create(c, c.taken_amount, currency) for c in consumed]

    def convert(self, convert: ConvertParams) -> List[ConsumedEntry]:
        total_to_reduce: Decimal = Decimal(convert.amount_from + convert.fee)

        consumed: List[ConsumedEntry] = self._consume_deposits(
            convert.currency_from, total_to_reduce
        )

        total_taken = sum(c.taken_amount for c in consumed)
        adjusted_consumed: List[ConsumedEntry] = []

        for c in consumed:
            amount_to = (c.taken_amount / total_taken) * convert.amount_to
            adjusted_consumed.append(
                ConsumedEntry(
                    tx_id=c.tx_id,
                    original_amount=c.original_amount,
                    taken_amount=c.taken_amount,
                    currency=convert.currency_from,
                    amount_to=amount_to,
                )
            )

            self.deposit(
                IncomingDepositParams(
                    tx_id=c.tx_id,
                    currency=convert.currency_to,
                    amount=amount_to,
                    fee=Decimal("0"),
                )
            )

        return adjusted_consumed
