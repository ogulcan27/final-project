from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import db
from app.services import TradeError, execute_trade, get_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: Literal["buy", "sell"]


@router.get("")
async def portfolio(request: Request) -> dict:
    return get_portfolio(request.app.state.price_cache)


@router.post("/trade")
async def trade(body: TradeRequest, request: Request) -> dict:
    cache = request.app.state.price_cache
    try:
        result = execute_trade(cache, body.ticker, body.side, body.quantity)
    except TradeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"trade": result, "portfolio": get_portfolio(cache)}


@router.get("/history")
async def history() -> list[dict]:
    return db.get_snapshots()
