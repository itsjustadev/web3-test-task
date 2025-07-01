from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from typing import Any

from app.service import round6_up


class IncomingDepositParams(BaseModel):
    amount: Decimal
    currency: str
    tx_id: Any
    fee: Decimal = Decimal("0")


class ConvertParams(BaseModel):
    amount_from: Decimal
    currency_from: str
    amount_to: Decimal
    currency_to: str
    fee: Decimal


class WithdrawParams(BaseModel):
    amount: Decimal
    currency: str
    fee: Decimal


# class ConsumedEntry(BaseModel):
#     tx_id: UUID
#     original_amount: Decimal
#     taken_amount: Decimal
#     currency: str

#     @classmethod
#     def create(cls, obj, taken_amount: Decimal, currency: str) -> "ConsumedEntry":
#         return cls(
#             tx_id=obj.tx_id if hasattr(obj, "tx_id") else obj["tx_id"],
#             original_amount=(
#                 obj.original_amount
#                 if hasattr(obj, "original_amount")
#                 else obj["original_amount"]
#             ),
#             taken_amount=round6_up(taken_amount),
#             currency=currency,
#         )


class ConsumedEntry(BaseModel):
    tx_id: UUID
    original_amount: Decimal
    taken_amount: Decimal
    currency: str

    @classmethod
    def create(
        cls, obj: dict | object, taken_amount: Decimal, currency: str
    ) -> "ConsumedEntry":
        if isinstance(obj, dict):
            tx_id = obj.get("tx_id")
            original_amount = obj.get("original_amount")
        else:
            tx_id = getattr(obj, "tx_id", None)
            original_amount = getattr(obj, "original_amount", None)

        if tx_id is None or original_amount is None:
            raise ValueError(
                "tx_id and original_amount are required to create ConsumedEntry"
            )

        return cls(
            tx_id=tx_id,
            original_amount=original_amount,
            taken_amount=taken_amount,
            currency=currency,
        )
