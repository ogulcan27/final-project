from typing import Literal

from pydantic import BaseModel


class TradeRequest(BaseModel):
    """A trade the LLM wants executed."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistChange(BaseModel):
    """A watchlist change the LLM wants applied."""

    ticker: str
    action: Literal["add", "remove"]


class LLMResponse(BaseModel):
    """Structured output returned by the LLM."""

    message: str
    trades: list[TradeRequest] = []
    watchlist_changes: list[WatchlistChange] = []
