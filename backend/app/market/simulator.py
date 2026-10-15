import asyncio
import contextlib
import math
import random

from .cache import PriceCache
from .interface import MarketDataSource
from .seed_data import DEFAULT_PARAMS, GBM_PARAMS, SECTORS, SEED_PRICES

TICK_SECONDS = 0.5
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
TIME_SPEEDUP = 30
DT = TICK_SECONDS / TRADING_SECONDS_PER_YEAR * TIME_SPEEDUP

MARKET_WEIGHT = 0.3
SECTOR_WEIGHT = 0.3
EVENT_PROB = 0.0005


class SimulatorSource(MarketDataSource):
    """GBM price simulator with correlated moves and occasional jump events.

    Each tick: S_next = S * exp((mu - sigma^2 / 2) * dt + sigma * sqrt(dt) * z).
    The shock z mixes a market factor, a sector factor and noise, so it keeps
    unit variance while tickers in the same sector move together.
    """

    def __init__(self, cache: PriceCache, rng: random.Random | None = None) -> None:
        self.cache = cache
        self.rng = rng or random.Random()
        self._prices: dict[str, float] = {}  # unrounded internal state
        self._task: asyncio.Task | None = None

    @property
    def tickers(self) -> list[str]:
        return list(self._prices)

    async def start(self, tickers: list[str]) -> None:
        for ticker in tickers:
            self._seed(ticker)
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._prices:
            self._seed(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._prices.pop(ticker, None)
        self.cache.remove(ticker)

    def _seed(self, ticker: str) -> None:
        price = SEED_PRICES.get(ticker) or round(self.rng.uniform(50, 300), 2)
        self._prices[ticker] = price
        self.cache.update(ticker, price, prev_close=price)

    async def _run(self) -> None:
        while True:
            self.step()
            await asyncio.sleep(TICK_SECONDS)

    def step(self) -> None:
        """Advance every ticker by one tick and write to the cache."""
        market_z = self.rng.gauss(0, 1)
        sector_z: dict[str, float] = {}
        for ticker, price in self._prices.items():
            mu, sigma = GBM_PARAMS.get(ticker, DEFAULT_PARAMS)
            z = self._correlated_shock(ticker, market_z, sector_z)
            price *= math.exp((mu - 0.5 * sigma**2) * DT + sigma * math.sqrt(DT) * z)
            if self.rng.random() < EVENT_PROB:
                price *= 1 + self.rng.choice([-1, 1]) * self.rng.uniform(0.02, 0.05)
            self._prices[ticker] = price
            self.cache.update(ticker, round(price, 2))

    def _correlated_shock(
        self, ticker: str, market_z: float, sector_z: dict[str, float]
    ) -> float:
        sector = SECTORS.get(ticker)
        sector_weight = SECTOR_WEIGHT if sector else 0.0
        if sector and sector not in sector_z:
            sector_z[sector] = self.rng.gauss(0, 1)
        noise = self.rng.gauss(0, 1)
        return (
            math.sqrt(MARKET_WEIGHT) * market_z
            + math.sqrt(sector_weight) * sector_z.get(sector, 0.0)
            + math.sqrt(1 - MARKET_WEIGHT - sector_weight) * noise
        )
