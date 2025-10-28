"""Bot implementation that orchestrates Azure OpenAI responses."""
from __future__ import annotations

from typing import List

from botbuilder.core import (ActivityHandler, ConversationState, MessageFactory,
                             TurnContext)
from botbuilder.schema import ChannelAccount

from .generative_service import AzureOpenAIService


class GenerativeAIBot(ActivityHandler):
    """A conversational bot that optionally calls Azure OpenAI for replies."""

    def __init__(self, conversation_state: ConversationState, generative_service: AzureOpenAIService) -> None:
        super().__init__()
        self._conversation_state = conversation_state
        self._generative_service = generative_service
        self._history_accessor = self._conversation_state.create_property("ConversationHistory")

    async def on_turn(self, turn_context: TurnContext) -> None:
        await super().on_turn(turn_context)
        await self._conversation_state.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        text = (turn_context.activity.text or "").strip()
        history: List[dict] = await self._history_accessor.get(turn_context, [])
        history.append({"role": "user", "content": text})

        reply = await self._generative_service.generate_reply(history)
        if reply is None:
            reply = f"You said: {text}" if text else "I did not receive any text to process."
        history.append({"role": "assistant", "content": reply})
        if len(history) > 40:
            history = history[-40:]

        await turn_context.send_activity(MessageFactory.text(reply))
        await self._history_accessor.set(turn_context, history)

    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(
                        "Hello! I'm a Python bot. Send me a message to start a conversation."
                    )
                )
