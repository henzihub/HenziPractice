"""aiohttp entrypoint for running the bot locally."""
from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from botbuilder.core import ConversationState, MemoryStorage, TurnContext
from botbuilder.integration.aiohttp import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

from .config import Config
from .generative_ai_bot import GenerativeAIBot
from .generative_service import AzureOpenAIService

_LOGGER = logging.getLogger(__name__)


async def create_app() -> web.Application:
    """Create and configure the aiohttp application that hosts the bot."""

    config = Config()
    adapter_settings = BotFrameworkAdapterSettings(config.microsoft_app_id, config.microsoft_app_password)
    adapter = BotFrameworkAdapter(adapter_settings)

    async def on_error(context: TurnContext, error: Exception) -> None:  # pragma: no cover - framework hook
        _LOGGER.exception("Unhandled error: %s", error)
        await context.send_activity("Oops. Something went wrong.")

    adapter.on_turn_error = on_error

    memory = MemoryStorage()
    conversation_state = ConversationState(memory)
    generative_service = AzureOpenAIService(config)
    bot = GenerativeAIBot(conversation_state, generative_service)

    async def messages(req: web.Request) -> web.Response:
        if "application/json" in req.headers.get("Content-Type", ""):
            body = await req.json()
        else:
            return web.Response(status=415)
        activity = Activity().deserialize(body)
        auth_header = req.headers.get("Authorization", "")

        async def aux_logic(turn_context):
            await bot.on_turn(turn_context)

        response = await adapter.process_activity(activity, auth_header, aux_logic)
        if response:
            return web.json_response(data=response.body, status=response.status)
        return web.Response(status=201)

    app = web.Application()
    app.router.add_post("/api/messages", messages)

    async def on_cleanup(app: web.Application) -> None:  # pragma: no cover - framework hook
        await conversation_state.close()
        await memory.close()

    app.on_cleanup.append(on_cleanup)
    _LOGGER.info("Bot application initialized (OpenAI configured=%s)", generative_service.is_configured())
    return app


def main() -> None:
    """Run the aiohttp web server."""

    logging.basicConfig(level=logging.INFO)
    app = asyncio.run(create_app())
    config = Config()
    web.run_app(app, host="0.0.0.0", port=config.port)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
