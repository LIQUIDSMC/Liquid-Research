"""
Market Data Platform — Canonical Schema (Phase 0, Binance)
platform/market_data/schema.py

Concrete schema for Phase 0's single source: Binance. Per
zROADMAP.md, cross-source generalization is explicitly a Phase 3
question, not answered here.

Each record distinguishes two kinds of canonical fact, documented
per-field rather than structurally separated: transport/
traceability facts (first_update_id, final_update_id,
previous_final_update_id — required for gap detection and tracing
a record to its originating message) and market facts (side,
price, quantity — properties of the market itself). Both kinds are
canonical, since losing either makes something permanently
unrecoverable, but they are conceptually distinct.

Numeric values are Decimal, validated positively via isinstance(),
per the Numeric Precision principle.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


def _validate_decimal(value, field_name: str) -> None:
    """
    Positively validate that value is a Decimal instance — not
    merely "not a float." Rejects str, int, float, and any other
    type that isn't actually Decimal, per the Numeric Precision
    principle.
    """
    if not isinstance(value, Decimal):
        raise ValueError(
            f"{field_name} must be a Decimal instance, got "
            f"{type(value).__name__} ({value!r}). Numeric values must be "
            f"Decimal, constructed directly from the source system's "
            f"transmitted string, per the Numeric Precision principle "
            f"in zROADMAP.md."
        )


@dataclass(frozen=True)
class DepthLevelRecord:
    """
    One canonical unit of observation: a single price level's new
    quantity, extracted from a Binance depthUpdate message. A
    single depthUpdate can report multiple level changes; each
    becomes its own DepthLevelRecord, sharing the same
    first_update_id / final_update_id / previous_final_update_id.

    Fields:
        timestamp_received (float): local receipt time. Not
            reported by Binance — assigned locally.
        event_time (float): Binance's "E" field.
        transaction_time (Optional[float]): Binance's "T" field,
            where provided.

        --- Transport/traceability facts (not market facts) ---
        first_update_id (int): Binance's "U" — first update ID in
            the originating message.
        final_update_id (int): Binance's "u" — final update ID in
            the originating message.
        previous_final_update_id (Optional[int]): Binance's "pu" —
            the previous message's final update ID, where provided.
            Canonical because losing it makes gap detection and
            replay verification permanently impossible after the
            fact — but it is a fact about message delivery, not
            about the market.

        --- Market facts ---
        side (str): "bid" or "ask" — a direct structural fact of
            which array (b or a) the level was reported in, not an
            inference.
        price (Decimal): the price level.
        quantity (Decimal): the new quantity at this price level.
            A quantity of zero means this level has been removed.
    """
    timestamp_received: float
    event_time: float
    transaction_time: Optional[float]
    first_update_id: int
    final_update_id: int
    previous_final_update_id: Optional[int]
    side: str
    price: Decimal
    quantity: Decimal

    def __post_init__(self):
        """Platform-wide invariants only."""
        if self.side not in ("bid", "ask"):
            raise ValueError(f"side must be 'bid' or 'ask', got '{self.side}'.")
        _validate_decimal(self.price, "price")
        _validate_decimal(self.quantity, "quantity")
        if self.price < 0:
            raise ValueError(f"price cannot be negative: {self.price}")
        if self.quantity < 0:
            raise ValueError(f"quantity cannot be negative: {self.quantity}")


@dataclass(frozen=True)
class TradeRecord:
    """
    One canonical unit of observation: a single trade, from a
    Binance trade message.

    Fields:
        timestamp_received (float): local receipt time.
        event_time (float): Binance's "E" field.
        trade_time (Optional[float]): Binance's "T" field.
        trade_id (int): Binance's "t" field — exchange-assigned identifier for this trade. Preserved because it is part of the observable event and cannot be re-derived once lost.
        price (Decimal): trade price. Market fact.
        quantity (Decimal): trade quantity. Market fact.
        is_buyer_maker (bool): Binance's "m" field — market fact,
            preserved because it is not derivable from other
            preserved fields.
    """
    timestamp_received: float
    event_time: float
    trade_time: Optional[float]
    trade_id: int
    price: Decimal
    quantity: Decimal
    is_buyer_maker: bool

    def __post_init__(self):
        """Platform-wide invariants only."""
        _validate_decimal(self.price, "price")
        _validate_decimal(self.quantity, "quantity")
        if self.price < 0:
            raise ValueError(f"price cannot be negative: {self.price}")
        if self.quantity < 0:
            raise ValueError(f"quantity cannot be negative: {self.quantity}")


if __name__ == "__main__":
    depth_record = DepthLevelRecord(
        timestamp_received=1720000000.0,
        event_time=1720000000123.0,
        transaction_time=1720000000120.0,
        first_update_id=157,
        final_update_id=160,
        previous_final_update_id=149,
        side="bid",
        price=Decimal("0.0024"),
        quantity=Decimal("10"),
    )
    print("Valid DepthLevelRecord created:", depth_record)

    trade_record = TradeRecord(
        timestamp_received=1720000000.0,
        event_time=1773110023891.0,
        trade_time=1773110023877.0,
        trade_id=19911650,
        price=Decimal("8.40000000"),
        quantity=Decimal("0.97915700"),
        is_buyer_maker=False,
    )
    print("Valid TradeRecord created:", trade_record)

    try:
        DepthLevelRecord(
            timestamp_received=1720000000.0,
            event_time=1720000000123.0,
            transaction_time=None,
            first_update_id=157,
            final_update_id=160,
            previous_final_update_id=149,
            side="bid",
            price="1.0",
            quantity=Decimal("1.0"),
        )
        print("ERROR: str price was not rejected")
    except ValueError as e:
        print("Correctly rejected str price:", e)

    try:
        TradeRecord(
            timestamp_received=1720000000.0,
            event_time=1773110023891.0,
            trade_time=None,
            trade_id=1,
            price=1.23,
            quantity=Decimal("1.0"),
            is_buyer_maker=False,
        )
        print("ERROR: float price was not rejected")
    except ValueError as e:
        print("Correctly rejected float price:", e)
