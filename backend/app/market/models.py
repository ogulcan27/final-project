from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Latest price snapshot for one ticker.

    previous_price is the price before this update (drives the green/red flash).
    prev_close is the prior session close (drives daily change %).
    timestamp is unix seconds, set by the backend when the cache is written.
    """

    ticker: str
    price: float
    previous_price: float
    prev_close: float
    timestamp: float

    @property
    def direction(self) -> str:
        if self.price > self.previous_price:
            return "up"
        if self.price < self.previous_price:
            return "down"
        return "flat"

    @property
    def change_pct(self) -> float:
        """Percent change versus the previous session close."""
        if self.prev_close == 0:
            return 0.0
        return round((self.price - self.prev_close) / self.prev_close * 100, 3)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "prev_close": self.prev_close,
            "change_pct": self.change_pct,
            "direction": self.direction,
            "timestamp": self.timestamp,
        }
