from app import db, services
from app.market import MarketDataSource, PriceCache

from . import client
from .prompt import build_context, build_messages
from .schema import LLMResponse, TradeRequest, WatchlistChange


def watchlist_with_prices(cache: PriceCache) -> list[dict]:
    """Watchlist tickers with their latest cached prices."""
    items = []
    for ticker in db.get_watchlist():
        update = cache.get(ticker)
        items.append({
            "ticker": ticker,
            "price": update.price if update else None,
            "change_pct": update.change_pct if update else None,
        })
    return items


def run_trade(cache: PriceCache, trade: TradeRequest) -> dict:
    """Execute one LLM trade, reporting failures instead of raising."""
    result = {"ticker": trade.ticker.upper(), "side": trade.side, "quantity": trade.quantity,
              "price": None, "status": "executed", "error": None}
    try:
        result["price"] = services.execute_trade(cache, trade.ticker, trade.side, trade.quantity)["price"]
    except services.TradeError as exc:
        result.update(status="failed", error=str(exc))
    return result


async def run_watchlist_change(source: MarketDataSource, change: WatchlistChange) -> dict:
    """Apply one LLM watchlist change, reporting failures instead of raising."""
    result = {"ticker": change.ticker.upper(), "action": change.action, "status": "executed", "error": None}
    action = services.add_ticker if change.action == "add" else services.remove_ticker
    try:
        await action(source, change.ticker.upper())
    except services.WatchlistError as exc:
        result.update(status="failed", error=str(exc))
    return result


async def get_reply(cache: PriceCache, user_message: str) -> LLMResponse:
    """Ask the LLM (or the mock) for a structured reply."""
    if client.is_mock():
        return client.mock_response(user_message)
    context = build_context(services.get_portfolio(cache), watchlist_with_prices(cache))
    messages = build_messages(context, db.get_chat_messages(), user_message)
    return await client.call_llm(messages)


async def handle_chat(cache: PriceCache, source: MarketDataSource, user_message: str) -> dict:
    """Full chat turn: LLM call, auto-execute actions, persist messages."""
    reply = await get_reply(cache, user_message)
    trades = [run_trade(cache, t) for t in reply.trades]
    changes = [await run_watchlist_change(source, c) for c in reply.watchlist_changes]
    actions = {"trades": trades, "watchlist_changes": changes}
    db.insert_chat_message("user", user_message)
    db.insert_chat_message("assistant", reply.message, actions)
    return {"message": reply.message, **actions}
