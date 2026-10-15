import time

from .models import PriceUpdate


class PriceCache:
    """In-memory latest price per ticker. Single event loop, so no locking."""

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}

    def update(
        self, ticker: str, price: float, prev_close: float | None = None
    ) -> PriceUpdate:
        """Store a new price and keep the old price as previous_price.

        prev_close defaults to the cached value, or to price on first sight.
        """
        old = self._prices.get(ticker)
        if prev_close is None:
            prev_close = old.prev_close if old else price
        update = PriceUpdate(
            ticker=ticker,
            price=price,
            previous_price=old.price if old else price,
            prev_close=prev_close,
            timestamp=time.time(),
        )
        self._prices[ticker] = update
        return update

    def get(self, ticker: str) -> PriceUpdate | None:
        return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        update = self._prices.get(ticker)
        return update.price if update else None

    def all(self) -> list[PriceUpdate]:
        return list(self._prices.values())

    def remove(self, ticker: str) -> None:
        self._prices.pop(ticker, None)

    def __contains__(self, ticker: str) -> bool:
        return ticker in self._prices
