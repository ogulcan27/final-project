import asyncio
import math
import random

import pytest

from app.market import PriceCache
from app.market import simulator
from app.market.seed_data import GBM_PARAMS, SEED_PRICES
from app.market.simulator import DT, SimulatorSource


def make(seed: int = 1) -> tuple[PriceCache, SimulatorSource]:
    cache = PriceCache()
    return cache, SimulatorSource(cache, rng=random.Random(seed))


def log_returns(sim: SimulatorSource, tickers: list[str], steps: int) -> dict:
    series = {t: [] for t in tickers}
    prev = dict(sim._prices)
    for _ in range(steps):
        sim.step()
        for t in tickers:
            series[t].append(math.log(sim._prices[t] / prev[t]))
            prev[t] = sim._prices[t]
    return series


def corr(a: list[float], b: list[float]) -> float:
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    var_a = sum((x - ma) ** 2 for x in a)
    var_b = sum((y - mb) ** 2 for y in b)
    return cov / math.sqrt(var_a * var_b)


async def test_known_ticker_seeds_at_seed_price():
    cache, sim = make()
    await sim.add_ticker("AAPL")
    u = cache.get("AAPL")
    assert u.price == SEED_PRICES["AAPL"] and u.prev_close == SEED_PRICES["AAPL"]


async def test_unknown_ticker_gets_random_price_in_range():
    cache, sim = make()
    await sim.add_ticker("ZZZZ")
    assert 50 <= cache.get_price("ZZZZ") <= 300


async def test_add_ticker_is_idempotent():
    cache, sim = make()
    await sim.add_ticker("ZZZZ")
    first = cache.get_price("ZZZZ")
    await sim.add_ticker("ZZZZ")
    assert cache.get_price("ZZZZ") == first
    assert sim.tickers == ["ZZZZ"]


async def test_remove_ticker_clears_cache_and_is_idempotent():
    cache, sim = make()
    await sim.add_ticker("AAPL")
    await sim.remove_ticker("AAPL")
    await sim.remove_ticker("AAPL")
    assert "AAPL" not in cache and sim.tickers == []


async def test_prices_stay_positive_and_two_decimals():
    cache, sim = make()
    for t in ("AAPL", "TSLA", "ZZZZ"):
        await sim.add_ticker(t)
    for _ in range(5_000):
        sim.step()
    for u in cache.all():
        assert u.price > 0
        assert u.price == round(u.price, 2)


def test_step_keeps_prev_close_fixed():
    cache, sim = make()
    sim._seed("AAPL")
    for _ in range(100):
        sim.step()
    assert cache.get("AAPL").prev_close == SEED_PRICES["AAPL"]


def test_step_is_deterministic_for_same_seed():
    results = []
    for _ in range(2):
        cache, sim = make(seed=42)
        sim._seed("AAPL")
        for _ in range(50):
            sim.step()
        results.append(cache.get_price("AAPL"))
    assert results[0] == results[1]


def test_gbm_log_return_std_matches_sigma(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROB", 0.0)
    _, sim = make(seed=7)
    sim._seed("AAPL")
    logs = log_returns(sim, ["AAPL"], 20_000)["AAPL"]
    mean = sum(logs) / len(logs)
    std = math.sqrt(sum((x - mean) ** 2 for x in logs) / len(logs))
    expected = 0.25 * math.sqrt(DT)
    assert abs(std - expected) / expected < 0.05


class ZeroShocks(random.Random):
    """Random source whose gaussian shocks are always zero."""

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        return 0.0


def test_gbm_drift_term_is_exact(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROB", 0.0)
    sim = SimulatorSource(PriceCache(), rng=ZeroShocks())
    sim._seed("AAPL")
    sim.step()
    mu, sigma = GBM_PARAMS["AAPL"]
    expected = SEED_PRICES["AAPL"] * math.exp((mu - 0.5 * sigma**2) * DT)
    assert sim._prices["AAPL"] == pytest.approx(expected, rel=1e-12)


def test_same_sector_more_correlated_than_cross_sector(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROB", 0.0)
    _, sim = make(seed=3)
    for t in ("AAPL", "MSFT", "JPM"):
        sim._seed(t)
    series = log_returns(sim, ["AAPL", "MSFT", "JPM"], 20_000)
    same = corr(series["AAPL"], series["MSFT"])
    cross = corr(series["AAPL"], series["JPM"])
    assert abs(same - 0.6) < 0.05
    assert abs(cross - 0.3) < 0.05


def test_events_produce_large_jumps(monkeypatch):
    monkeypatch.setattr(simulator, "EVENT_PROB", 1.0)
    _, sim = make(seed=5)
    sim._seed("AAPL")
    series = log_returns(sim, ["AAPL"], 200)["AAPL"]
    assert all(abs(r) > 0.015 for r in series)
    assert any(r > 0 for r in series) and any(r < 0 for r in series)


async def test_start_seeds_and_runs_in_background(monkeypatch):
    monkeypatch.setattr(simulator, "TICK_SECONDS", 0.01)
    cache, sim = make()
    await sim.start(["AAPL", "MSFT"])
    assert set(sim.tickers) == {"AAPL", "MSFT"}
    first = cache.get("AAPL").timestamp
    await asyncio.sleep(0.1)
    assert cache.get("AAPL").timestamp > first
    await sim.stop()


async def test_stop_halts_updates_and_is_idempotent(monkeypatch):
    monkeypatch.setattr(simulator, "TICK_SECONDS", 0.01)
    cache, sim = make()
    await sim.start(["AAPL"])
    await sim.stop()
    await sim.stop()
    stamp = cache.get("AAPL").timestamp
    await asyncio.sleep(0.05)
    assert cache.get("AAPL").timestamp == stamp
