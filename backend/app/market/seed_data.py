"""Seed prices, GBM parameters and sector groups for the simulator."""

DEFAULT_TICKERS: list[str] = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX",
]

SEED_PRICES: dict[str, float] = {
    "AAPL": 190.0, "GOOGL": 175.0, "MSFT": 420.0, "AMZN": 185.0, "TSLA": 250.0,
    "NVDA": 120.0, "META": 500.0, "JPM": 200.0, "V": 275.0, "NFLX": 650.0,
}

# (annual drift mu, annual volatility sigma)
GBM_PARAMS: dict[str, tuple[float, float]] = {
    "AAPL": (0.08, 0.25), "GOOGL": (0.08, 0.28), "MSFT": (0.09, 0.24),
    "AMZN": (0.09, 0.30), "TSLA": (0.05, 0.55), "NVDA": (0.15, 0.50),
    "META": (0.10, 0.35), "JPM": (0.06, 0.22), "V": (0.07, 0.20),
    "NFLX": (0.08, 0.38),
}
DEFAULT_PARAMS: tuple[float, float] = (0.05, 0.30)

SECTORS: dict[str, str] = {
    "AAPL": "tech", "GOOGL": "tech", "MSFT": "tech", "AMZN": "tech",
    "TSLA": "tech", "NVDA": "tech", "META": "tech", "NFLX": "tech",
    "JPM": "finance", "V": "finance",
}
