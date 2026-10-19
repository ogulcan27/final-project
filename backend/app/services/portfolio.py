from app import db
from app.market import PriceCache


class TradeError(Exception):
    """A trade was rejected; the message is user-facing."""


def execute_trade(cache: PriceCache, ticker: str, side: str, quantity: float) -> dict:
    """Validate and fill a market order at the cached price, then record a snapshot."""
    ticker = ticker.strip().upper()
    price = cache.get_price(ticker)
    if price is None:
        raise TradeError(f"No price available for {ticker}")
    if quantity <= 0:
        raise TradeError("Quantity must be positive")
    if side == "buy":
        _buy(ticker, quantity, price)
    elif side == "sell":
        _sell(ticker, quantity, price)
    else:
        raise TradeError(f"Invalid side: {side}")
    trade = db.insert_trade(ticker, side, quantity, price)
    db.insert_snapshot(get_portfolio(cache)["total_value"])
    return trade


def _buy(ticker: str, quantity: float, price: float) -> None:
    cash = db.get_cash()
    cost = quantity * price
    if cost > cash:
        raise TradeError(f"Insufficient cash: need ${cost:,.2f}, have ${cash:,.2f}")
    position = db.get_position(ticker)
    old_qty = position["quantity"] if position else 0.0
    old_avg = position["avg_cost"] if position else 0.0
    new_qty = old_qty + quantity
    db.set_cash(cash - cost)
    db.save_position(ticker, new_qty, (old_qty * old_avg + cost) / new_qty)


def _sell(ticker: str, quantity: float, price: float) -> None:
    position = db.get_position(ticker)
    held = position["quantity"] if position else 0.0
    if quantity > held:
        raise TradeError(f"Insufficient shares: have {held:g} {ticker}, tried to sell {quantity:g}")
    db.set_cash(db.get_cash() + quantity * price)
    db.save_position(ticker, held - quantity, position["avg_cost"])


def get_portfolio(cache: PriceCache) -> dict:
    """Cash, positions valued at live prices, total value and unrealized P&L."""
    positions = [_value_position(p, cache) for p in db.get_positions()]
    cash = db.get_cash()
    return {
        "cash_balance": round(cash, 2),
        "total_value": round(cash + sum(p["market_value"] for p in positions), 2),
        "unrealized_pnl": round(sum(p["unrealized_pnl"] for p in positions), 2),
        "positions": positions,
    }


def _value_position(position: dict, cache: PriceCache) -> dict:
    """Value one position; falls back to avg_cost when no price is cached yet."""
    quantity, avg_cost = position["quantity"], position["avg_cost"]
    price = cache.get_price(position["ticker"]) or avg_cost
    pnl = (price - avg_cost) * quantity
    return {
        "ticker": position["ticker"],
        "quantity": quantity,
        "avg_cost": round(avg_cost, 4),
        "current_price": price,
        "market_value": round(price * quantity, 2),
        "unrealized_pnl": round(pnl, 2),
        "pnl_pct": round((price - avg_cost) / avg_cost * 100, 2),
    }
