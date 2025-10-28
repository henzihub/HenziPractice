"""Tests for the GenerativeAIBot conversation flow."""
from __future__ import annotations

import pytest
from botbuilder.core import ConversationState, MemoryStorage, TestAdapter

from bot.config import Config
from bot.generative_ai_bot import GenerativeAIBot
from bot.generative_service import AzureOpenAIService


class StubGenerativeService(AzureOpenAIService):
    def __init__(self, reply: str | None) -> None:
        self._reply = reply
        super().__init__(Config())

    def is_configured(self) -> bool:  # pragma: no cover - deterministic override
        return True

    async def generate_reply(self, history):  # type: ignore[override]
        return self._reply


@pytest.mark.asyncio
async def test_bot_uses_stubbed_reply():
    conversation_state = ConversationState(MemoryStorage())
    bot = GenerativeAIBot(conversation_state, StubGenerativeService("stub"))

    async def logic(turn_context):
        await bot.on_turn(turn_context)

    adapter = TestAdapter(logic)
    await adapter.test("hello", "stub")


@pytest.mark.asyncio
async def test_bot_falls_back_to_echo_when_none():
    conversation_state = ConversationState(MemoryStorage())
    bot = GenerativeAIBot(conversation_state, StubGenerativeService(None))

    async def logic(turn_context):
        await bot.on_turn(turn_context)

    adapter = TestAdapter(logic)
    await adapter.test("hello", "You said: hello")
