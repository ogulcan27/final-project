from app import db
from app.market import MarketDataSource


class WatchlistError(Exception):
    """A watchlist change was rejected; the message is user-facing."""


async def add_ticker(source: MarketDataSource, ticker: str) -> None:
    """Add a ticker to the watchlist and start tracking its price."""
    ticker = ticker.strip().upper()
    if not db.add_watchlist(ticker):
        raise WatchlistError(f"{ticker} is already in the watchlist")
    await source.add_ticker(ticker)


async def remove_ticker(source: MarketDataSource, ticker: str) -> None:
    """Remove a ticker from the watchlist; keep tracking it while a position is open."""
    ticker = ticker.strip().upper()
    if not db.remove_watchlist(ticker):
        raise WatchlistError(f"{ticker} is not in the watchlist")
    if db.get_position(ticker) is None:
        await source.remove_ticker(ticker)
