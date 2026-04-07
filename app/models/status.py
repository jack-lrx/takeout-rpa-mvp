from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NormalizedStatus(BaseModel):
    platform: str
    order_id: str
    status: str
    rider_status_text: str = Field(default="")
    event_time: str
    raw_payload: dict[str, Any] | list[Any] | str | int | float | bool | None = Field(default_factory=dict)
    pushed_to_erp: int = Field(default=0)

    model_config = ConfigDict(extra="allow")

    @field_validator("order_id", "status", mode="before")
    @classmethod
    def normalize_required_text(cls, value: Any) -> str:
        if value is None:
            raise ValueError("required field is missing")
        text = str(value).strip()
        if not text:
            raise ValueError("required field cannot be empty")
        return text

    @field_validator("rider_status_text", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("event_time", mode="before")
    @classmethod
    def normalize_event_time(cls, value: Any) -> str:
        if value in (None, ""):
            return datetime.now(timezone.utc).isoformat()
        if isinstance(value, (int, float)):
            timestamp = value / 1000 if value > 10_000_000_000 else value
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        text = str(value).strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return text
