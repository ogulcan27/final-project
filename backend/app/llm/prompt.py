import json

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation.

You can:
- Analyze portfolio composition, risk concentration and P&L
- Suggest trades with brief reasoning
- Execute trades when the user asks or agrees (market orders, instant fill)
- Manage the watchlist proactively (add or remove tickers)

Be concise and data-driven. Only trade with the cash and shares available.
Always respond with valid JSON matching the schema:
{"message": str, "trades": [{"ticker": str, "side": "buy"|"sell", "quantity": number}],
 "watchlist_changes": [{"ticker": str, "action": "add"|"remove"}]}
Use empty lists when no trades or watchlist changes are needed."""


def build_context(portfolio: dict, watchlist: list[dict]) -> str:
    """Render the user's portfolio and watchlist as a context message."""
    return "Current portfolio:\n" + json.dumps(
        {"portfolio": portfolio, "watchlist": watchlist}, indent=1
    )


def build_messages(context: str, history: list[dict], user_message: str) -> list[dict]:
    """Assemble system prompt, context, conversation history and the new message."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context},
    ]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": user_message})
    return messages
