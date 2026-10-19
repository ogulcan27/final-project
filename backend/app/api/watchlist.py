from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app import db
from app.market import PriceCache
from app.services import WatchlistError, add_ticker, remove_ticker

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddTickerRequest(BaseModel):
    ticker: str


def _item(cache: PriceCache, ticker: str) -> dict:
    """Watchlist row; price fields are None until the first tick."""
    update = cache.get(ticker)
    return {
        "ticker": ticker,
        "price": update.price if update else None,
        "previous_price": update.previous_price if update else None,
        "change_pct": update.change_pct if update else None,
        "direction": update.direction if update else None,
    }


@router.get("")
async def watchlist(request: Request) -> list[dict]:
    cache = request.app.state.price_cache
    return [_item(cache, t) for t in db.get_watchlist()]


@router.post("", status_code=201)
async def add(body: AddTickerRequest, request: Request) -> dict:
    try:
        await add_ticker(request.app.state.market_source, body.ticker)
    except WatchlistError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _item(request.app.state.price_cache, body.ticker.strip().upper())


@router.delete("/{ticker}", status_code=204)
async def remove(ticker: str, request: Request) -> Response:
    try:
        await remove_ticker(request.app.state.market_source, ticker)
    except WatchlistError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)
