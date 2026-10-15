from app.market import PriceCache, create_market_source
from app.market.massive import MassiveSource
from app.market.simulator import SimulatorSource


def test_empty_key_selects_simulator(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "")
    assert isinstance(create_market_source(PriceCache()), SimulatorSource)


def test_missing_key_selects_simulator(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    assert isinstance(create_market_source(PriceCache()), SimulatorSource)


def test_whitespace_key_selects_simulator(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "   ")
    assert isinstance(create_market_source(PriceCache()), SimulatorSource)


def test_key_selects_massive_with_poll_interval(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "abc")
    monkeypatch.setenv("MASSIVE_POLL_SECONDS", "5")
    source = create_market_source(PriceCache())
    assert isinstance(source, MassiveSource)
    assert source.poll_seconds == 5.0


def test_default_poll_interval(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "abc")
    monkeypatch.delenv("MASSIVE_POLL_SECONDS", raising=False)
    assert create_market_source(PriceCache()).poll_seconds == 15.0
