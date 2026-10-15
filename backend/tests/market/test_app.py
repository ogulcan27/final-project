import httpx

from app.main import app, lifespan
from app.market.seed_data import DEFAULT_TICKERS
from app.market.simulator import SimulatorSource


async def test_lifespan_starts_simulator_with_default_tickers(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    async with lifespan(app):
        assert isinstance(app.state.market_source, SimulatorSource)
        assert set(app.state.market_source.tickers) == set(DEFAULT_TICKERS)
        assert len(app.state.price_cache.all()) == len(DEFAULT_TICKERS)


async def test_health_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.json() == {"status": "ok"}
