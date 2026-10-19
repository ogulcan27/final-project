from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import db

from .chat import handle_chat

router = APIRouter(prefix="/api/chat")


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(body: ChatRequest, request: Request) -> dict:
    """Send a message to FinAlly and get the reply plus executed actions."""
    state = request.app.state
    return await handle_chat(state.price_cache, state.market_source, body.message)


@router.get("/history")
async def history() -> list[dict]:
    """Recent conversation history, oldest first."""
    return db.get_chat_messages()
