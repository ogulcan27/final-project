from types import SimpleNamespace

import pytest

from app import db
from app.llm import chat, client
from app.llm.schema import LLMResponse
from app.market import PriceCache


class FakeSource:
    """Records ticker adds/removes instead of producing prices."""

    def __init__(self) -> None:
        self.added: list[str] = []

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        pass


@pytest.fixture
def cache(tmp_path, monkeypatch) -> PriceCache:
    monkeypatch.setenv("FINALLY_DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    return cache


def fake_llm(monkeypatch, content: str) -> list:
    """Replace the LiteLLM call with one returning content; capture the kwargs."""
    calls = []

    async def fake_acompletion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    monkeypatch.setenv("LLM_MOCK", "false")
    monkeypatch.setattr(client, "acompletion", fake_acompletion)
    return calls


def test_parse_full_schema():
    content = '{"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 2.5}],' \
              ' "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]}'
    reply = client.parse_response(content)
    assert reply.trades[0].quantity == 2.5
    assert reply.watchlist_changes[0].action == "add"


def test_parse_message_only_defaults_empty_lists():
    reply = client.parse_response('{"message": "hi"}')
    assert reply == LLMResponse(message="hi")


@pytest.mark.parametrize("content", ["not json", '{"trades": []}', '{"message": "x", "trades": [{"side": "hold"}]}'])
def test_parse_malformed_falls_back_to_text(content):
    reply = client.parse_response(content)
    assert reply.message == content
    assert reply.trades == [] and reply.watchlist_changes == []


@pytest.mark.parametrize(("text", "side"), [("please buy", "buy"), ("Sell now", "sell")])
def test_mock_trades(text, side):
    reply = client.mock_response(text)
    assert [(t.ticker, t.side, t.quantity) for t in reply.trades] == [("AAPL", side, 1)]


def test_mock_watch_and_default():
    assert client.mock_response("watch paypal").watchlist_changes[0].ticker == "PYPL"
    assert client.mock_response("hello") == LLMResponse(message="Mock response: hello")


async def test_mock_chat_executes_buy_and_stores_messages(cache, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    result = await chat.handle_chat(cache, FakeSource(), "buy something")
    assert result["trades"] == [{"ticker": "AAPL", "side": "buy", "quantity": 1, "price": 100.0,
                                 "status": "executed", "error": None}]
    assert db.get_cash() == 9900.0
    history = db.get_chat_messages()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["actions"]["trades"][0]["status"] == "executed"


async def test_failed_trade_is_reported(cache, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    result = await chat.handle_chat(cache, FakeSource(), "sell it")
    trade = result["trades"][0]
    assert trade["status"] == "failed"
    assert trade["error"]


async def test_mock_watch_adds_ticker(cache, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    source = FakeSource()
    result = await chat.handle_chat(cache, source, "watch PYPL")
    assert result["watchlist_changes"][0]["status"] == "executed"
    assert source.added == ["PYPL"]
    assert "PYPL" in db.get_watchlist()

    again = await chat.handle_chat(cache, source, "watch PYPL")
    assert again["watchlist_changes"][0]["status"] == "failed"


async def test_real_path_sends_structured_request(cache, monkeypatch):
    calls = fake_llm(monkeypatch, '{"message": "Bought.", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 3}]}')
    result = await chat.handle_chat(cache, FakeSource(), "get me some apple")
    kwargs = calls[0]
    assert kwargs["model"] == client.MODEL
    assert kwargs["response_format"] is LLMResponse
    assert kwargs["extra_body"] == {"provider": {"require_parameters": True}}
    assert kwargs["messages"][0]["content"].startswith("You are FinAlly")
    assert "cash_balance" in kwargs["messages"][1]["content"]
    assert kwargs["messages"][-1] == {"role": "user", "content": "get me some apple"}
    assert result["message"] == "Bought."
    assert result["trades"][0]["status"] == "executed"


async def test_real_path_includes_history(cache, monkeypatch):
    db.insert_chat_message("user", "earlier question")
    db.insert_chat_message("assistant", "earlier answer")
    calls = fake_llm(monkeypatch, '{"message": "ok"}')
    await chat.handle_chat(cache, FakeSource(), "next")
    contents = [m["content"] for m in calls[0]["messages"]]
    assert contents[2:] == ["earlier question", "earlier answer", "next"]


async def test_malformed_llm_output_still_replies(cache, monkeypatch):
    fake_llm(monkeypatch, "plain text answer")
    result = await chat.handle_chat(cache, FakeSource(), "hi")
    assert result == {"message": "plain text answer", "trades": [], "watchlist_changes": []}
