import os

from litellm import acompletion

from .schema import LLMResponse, TradeRequest, WatchlistChange

MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
EXTRA_BODY = {"provider": {"require_parameters": True}}


def is_mock() -> bool:
    return os.getenv("LLM_MOCK", "false").lower() == "true"


def mock_response(user_message: str) -> LLMResponse:
    """Deterministic keyword-based response for tests (see TEAM_CONTRACTS.md)."""
    text = user_message.lower()
    if "buy" in text:
        return LLMResponse(
            message="Mock response: buying 1 share of AAPL.",
            trades=[TradeRequest(ticker="AAPL", side="buy", quantity=1)],
        )
    if "sell" in text:
        return LLMResponse(
            message="Mock response: selling 1 share of AAPL.",
            trades=[TradeRequest(ticker="AAPL", side="sell", quantity=1)],
        )
    if "watch" in text:
        return LLMResponse(
            message="Mock response: adding PYPL to your watchlist.",
            watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
        )
    return LLMResponse(message=f"Mock response: {user_message}")


def parse_response(content: str) -> LLMResponse:
    """Parse the model's JSON; fall back to plain text if it is malformed."""
    try:
        return LLMResponse.model_validate_json(content)
    except ValueError:
        return LLMResponse(message=content or "Sorry, I could not produce a response.")


async def call_llm(messages: list[dict]) -> LLMResponse:
    """Call OpenRouter via LiteLLM with Structured Outputs."""
    response = await acompletion(
        model=MODEL, messages=messages, response_format=LLMResponse, extra_body=EXTRA_BODY
    )
    return parse_response(response.choices[0].message.content)
