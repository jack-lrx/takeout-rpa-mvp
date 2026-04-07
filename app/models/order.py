from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderItem(BaseModel):
    name: str = Field(default="")
    quantity: float = Field(default=1.0)
    unit_price: float | None = Field(default=None)
    raw_item: dict[str, Any] | Any = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow")

    @field_validator("quantity", mode="before")
    @classmethod
    def normalize_quantity(cls, value: Any) -> float:
        if value in (None, "", False):
            return 1.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1.0

    @field_validator("unit_price", mode="before")
    @classmethod
    def normalize_unit_price(cls, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


class NormalizedOrder(BaseModel):
    platform: str
    order_id: str
    items: list[OrderItem] = Field(default_factory=list)
    amount: float = Field(default=0.0)
    expected_income: float = Field(default=0.0)
    raw_payload: dict[str, Any] | list[Any] | str | int | float | bool | None
    pushed_to_erp: int = Field(default=0)

    model_config = ConfigDict(extra="allow")

    @field_validator("order_id", mode="before")
    @classmethod
    def normalize_order_id(cls, value: Any) -> str:
        if value is None:
            raise ValueError("order_id is required")
        order_id = str(value).strip()
        if not order_id:
            raise ValueError("order_id cannot be empty")
        return order_id

    @field_validator("amount", "expected_income", mode="before")
    @classmethod
    def normalize_amount(cls, value: Any) -> float:
        if value in (None, ""):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
