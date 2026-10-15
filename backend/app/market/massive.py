import asyncio
import contextlib
import logging

import httpx

from .cache import PriceCache
from .interface import MarketDataSource

log = logging.getLogger(__name__)

BASE_URL = "https://api.massive.com"
SNAPSHOT_PATH = "/v2/snapshot/locale/us/markets/stocks/tickers"


def parse_snapshot(payload: dict) -> dict[str, tuple[float, float]]:
    """Map a snapshot response to {ticker: (price, prev_close)}.

    Price falls back from last trade to minute close, day close, previous close.
    Entries with no usable price are skipped.
    """
    result: dict[str, tuple[float, float]] = {}
    for item in payload.get("tickers", []):
        prev_close = (item.get("prevDay") or {}).get("c") or 0.0
        candidates = [
            (item.get("lastTrade") or {}).get("p"),
            (item.get("min") or {}).get("c"),
            (item.get("day") or {}).get("c"),
            prev_close,
        ]
        price = next((p for p in candidates if p), None)
        if price:
            result[item["ticker"]] = (float(price), float(prev_close or price))
    return result


class MassiveSource(MarketDataSource):
    """Polls the Massive REST snapshot endpoint for the union of tracked tickers."""

    def __init__(
        self,
        cache: PriceCache,
        api_key: str,
        poll_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.cache = cache
        self.poll_seconds = poll_seconds
        self._tickers: set[str] = set()
        self._task: asyncio.Task | None = None
        self._client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )

    @property
    def tickers(self) -> list[str]:
        return sorted(self._tickers)

    async def start(self, tickers: list[str]) -> None:
        self._tickers = set(tickers)
        await self.poll_once()  # prime the cache so the first SSE push has data
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._client.aclose()

    async def add_ticker(self, ticker: str) -> None:
        self._tickers.add(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker)
        self.cache.remove(ticker)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.poll_seconds)
            await self.poll_once()

    async def poll_once(self) -> None:
        """One snapshot request for all tracked tickers.

        Failures are logged, not raised, so one bad poll never stops polling.
        """
        if not self._tickers:
            return
        try:
            resp = await self._client.get(
                SNAPSHOT_PATH, params={"tickers": ",".join(sorted(self._tickers))}
            )
            resp.raise_for_status()
            prices = parse_snapshot(resp.json())
        except httpx.HTTPError as exc:
            log.warning("Massive poll failed: %s", exc)
            return
        except Exception:
            log.exception("Unexpected Massive response")
            return
        for ticker, (price, prev_close) in prices.items():
            if ticker in self._tickers:
                self.cache.update(ticker, price, prev_close=prev_close)
