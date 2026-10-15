import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive import MassiveSource
from .simulator import SimulatorSource


def create_market_source(cache: PriceCache) -> MarketDataSource:
    """Massive if MASSIVE_API_KEY is set and non-empty, else the simulator."""
    api_key = os.getenv("MASSIVE_API_KEY", "").strip()
    if api_key:
        poll = float(os.getenv("MASSIVE_POLL_SECONDS", "15"))
        return MassiveSource(cache, api_key, poll_seconds=poll)
    return SimulatorSource(cache)
