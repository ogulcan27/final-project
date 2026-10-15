from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """A background producer that keeps a PriceCache fresh.

    Implementations receive the cache in their constructor and write to it.
    Tickers are upper case; the API layer normalizes them.
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing prices for the given tickers (spawns a background task)."""

    @abstractmethod
    async def stop(self) -> None:
        """Cancel the background task and release resources."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Start tracking a ticker. Idempotent."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking a ticker and drop it from the cache. Idempotent."""

    @property
    @abstractmethod
    def tickers(self) -> list[str]:
        """Currently tracked tickers."""
