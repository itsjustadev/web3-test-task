from abc import ABC, abstractmethod
from uuid import UUID
from decimal import Decimal
from typing import Deque, Dict, List, Literal

from app.schemas import (
    IncomingDepositParams,
    ConvertParams,
    WithdrawParams,
    ConsumedEntry,
)
from app.exceptions import WithdrawalError
from app.service import round6_up


class Wallet(ABC):
    @abstractmethod
    def deposit(self, deposit: IncomingDepositParams) -> None:
        pass

    @abstractmethod
    def convert(self, convert: ConvertParams) -> List[ConsumedEntry]:
        pass

    @abstractmethod
    def withdraw(self, withdraw: WithdrawParams) -> List[ConsumedEntry]:
        pass

    @abstractmethod
    def balance(self) -> dict:
        pass


class DepositQueueMixin:
    def __init__(self) -> None:
        self.deposits: Dict[str, Deque[DepositEntry]] = {}

    def _check_currency_exists(self, currency: str) -> None:
        if currency not in self.deposits:
            raise ValueError(f"Нет средств в валюте {currency}")

    def _check_sufficient_funds(self, currency: str, total_to_reduce: Decimal) -> None:
        total_available: Decimal | Literal[0] = sum(
            d.remaining_amount for d in self.deposits[currency]
        )
        if total_available < total_to_reduce:
            raise ValueError(
                f"Недостаточно средств: доступно {total_available}, необходимо {total_to_reduce}"
            )

    def _consume_deposits(
        self, currency: str, total_to_reduce: Decimal
    ) -> List[ConsumedEntry]:
        consumed = []
        remaining = total_to_reduce

        while remaining > Decimal("0") and self.deposits[currency]:
            deposit: DepositEntry = self.deposits[currency][0]
            taken: Decimal = deposit.consume(remaining)
            remaining: Decimal = round6_up(remaining - taken)

            consumed.append(ConsumedEntry.create(deposit, taken, currency))

            if deposit.is_empty():
                self.deposits[currency].popleft()

        if remaining > Decimal("0"):
            raise WithdrawalError("Ошибка: снятие средств выполнено не полностью")

        return consumed


class DepositEntry:
    def __init__(self, deposit: IncomingDepositParams):
        self.tx_id: UUID = deposit.tx_id
        self.currency: str = deposit.currency
        self.original_amount: Decimal = round6_up(deposit.amount - deposit.fee)
        self.remaining_amount: Decimal = self.original_amount

    def consume(self, amount: Decimal) -> Decimal:
        taken: Decimal = min(self.remaining_amount, amount)
        self.remaining_amount = round6_up(self.remaining_amount - taken)
        return taken

    def is_empty(self) -> bool:
        return self.remaining_amount == Decimal("0")
