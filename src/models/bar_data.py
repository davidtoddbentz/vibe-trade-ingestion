"""Bar data model for ClickHouse storage."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class BarData(BaseModel):
    """Validated bar data structure for ClickHouse."""

    instrument_id: str = Field(..., description="Instrument identifier (e.g., BTC-USD)")
    ts: datetime = Field(..., description="Timestamp")
    o: float = Field(..., ge=0, description="Open price")
    h: float = Field(..., ge=0, description="High price")
    l: float = Field(..., ge=0, description="Low price")
    c: float = Field(..., ge=0, description="Close price")
    volume_base: float = Field(..., ge=0, description="Base volume")
    volume_quote: float = Field(..., ge=0, description="Quote volume")

    @field_validator("h")
    @classmethod
    def high_must_be_greater_than_or_equal_to_open_close(cls, v, info):
        """Validate that high >= max(open, close)."""
        if "o" in info.data and "c" in info.data:
            max_oc = max(info.data["o"], info.data["c"])
            if v < max_oc:
                raise ValueError(f"High ({v}) must be >= max(open, close) ({max_oc})")
        return v

    @field_validator("l")
    @classmethod
    def low_must_be_less_than_or_equal_to_open_close(cls, v, info):
        """Validate that low <= min(open, close)."""
        if "c" in info.data and "o" in info.data:
            min_oc = min(info.data["o"], info.data["c"])
            if v > min_oc:
                raise ValueError(f"Low ({v}) must be <= min(open, close) ({min_oc})")
        return v

