import asyncio
import re
from dataclasses import dataclass
from functools import wraps
from typing import Any

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from pyrogram import Client, enums, filters, idle
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from .config import Settings
from .mentor import MentorService
from .text_utils import split_long_message


COMMAND_NAMES = ("start", "help", "status", "reset", "ask")
NON_COMMAND_TEXT_FILTER = filters.text & ~filters.command(list(COMMAND_NAMES))


@dataclass(frozen=True)
class RouteSpec:
    route_filter: Any
    group: int = 0


def message_route(route_filter: Any, group: int = 0):
    def decorator(func):
        route_specs = list(getattr(func, "__route_specs__", []))
        route_specs.append(RouteSpec(route_filter=route_filter, group=group))
        setattr(func, "__route_specs__", route_specs)
        return func

    return decorator


def command_route(*commands: str, group: int = 0):
    return message_route(filters.command(list(commands)), group=group)


def with_typing_action(func):
    @wraps(func)
    async def wrapper(self, client: Client, message: Message, *args, **kwargs):
        await client.send_chat_action(message.chat.id, enums.ChatAction.TYPING)
        return await func(self, client, message, *args, **kwargs)

    return wrapper


class AcpcMentorBotApp:
    def __init__(self, settings: Settings, mentor_service: MentorService) -> None:
        self.settings = settings
        self.mentor_service = mentor_service
        self.bot_username = ""
        self.client = Client(
            name=self.settings.telegram_session_name,
            api_id=self.settings.telegram_api_id,
            api_hash=self.settings.telegram_api_hash,
            bot_token=self.settings.telegram_bot_token,
            workdir=str(self.settings.telegram_workdir),
        )
        self._register_handlers()

    def _register_handlers(self) -> None:
        for cls in reversed(type(self).__mro__):
            for name, member in cls.__dict__.items():
                route_specs = getattr(member, "__route_specs__", [])
                if not route_specs:
                    continue

                bound_method = getattr(self, name)
                for route_spec in route_specs:
                    self.client.add_handler(
                        MessageHandler(bound_method, route_spec.route_filter),
                        group=route_spec.group,
                    )

    @command_route("start")
    async def _handle_start(self, _client: Client, message: Message) -> None:
        await self._reply(
            message,
            (
                "ACPC mentor bot is ready.\n"
                "Send a problem question, a failing idea, or your C++ code.\n"
                "In groups, use /ask <question>, mention the bot, or reply to one of its messages."
            ),
        )

    @command_route("help")
    async def _handle_help(self, _client: Client, message: Message) -> None:
        await self._reply(
            message,
            (
                "Usage:\n"
                "- Ask about a problem, constraint, edge case, or algorithm choice.\n"
                "- Paste code for review.\n"
                "- /ask <question> works well in groups.\n"
                "- /status shows the current provider and loaded knowledge.\n"
                "- /reset clears this chat's short memory."
            ),
        )

    @command_route("status")
    async def _handle_status(self, _client: Client, message: Message) -> None:
        await self._reply(message, self.mentor_service.status_text())

    @command_route("reset")
    async def _handle_reset(self, _client: Client, message: Message) -> None:
        self.mentor_service.reset_history(message.chat.id)
        await self._reply(message, "Short-term conversation memory cleared.")

    @command_route("ask")
    async def _handle_ask(self, client: Client, message: Message) -> None:
        question = self._extract_command_argument(message.text or "", "ask")
        if not question:
            await self._reply(message, "Use /ask followed by your question.")
            return
        await self._answer_message(client, message, question)

    @message_route(NON_COMMAND_TEXT_FILTER)
    async def _handle_text(self, client: Client, message: Message) -> None:
        question = self._extract_question(message)
        if not question:
            return
        await self._answer_message(client, message, question)

    @with_typing_action
    async def _answer_message(self, client: Client, message: Message, question: str) -> None:
        answer = await asyncio.to_thread(
            self.mentor_service.answer_question,
            message.chat.id,
            question,
        )
        await self._reply(message, answer)

    def _extract_question(self, message: Message) -> str:
        text = (message.text or "").strip()
        if not text:
            return ""

        if message.chat.type == enums.ChatType.PRIVATE:
            return text

        reply_to = message.reply_to_message
        reply_username = ""
        if reply_to and reply_to.from_user and reply_to.from_user.username:
            reply_username = reply_to.from_user.username.lower()
        if reply_username and reply_username == self.bot_username:
            return text

        lowered = text.lower()
        if self.bot_username and f"@{self.bot_username}" in lowered:
            return re.sub(rf"@{re.escape(self.bot_username)}", "", text, flags=re.IGNORECASE).strip()

        return ""

    @staticmethod
    def _extract_command_argument(text: str, command: str) -> str:
        match = re.match(rf"^/{command}(?:@\w+)?\s+(.*)$", text.strip(), flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return match.group(1).strip()

    async def _reply(self, message: Message, text: str) -> None:
        for part in split_long_message(text, self.settings.telegram_send_limit):
            await message.reply_text(part, disable_web_page_preview=True)

    async def _serve(self) -> None:
        await self.client.start()
        me = await self.client.get_me()
        self.bot_username = (me.username or "").lower()

        print(f"Bot username: @{self.bot_username}")
        print(f"Provider: {self.settings.resolved_provider()}")
        print(f"Model: {self.settings.resolved_model()}")
        print(f"Knowledge chunks loaded: {len(self.mentor_service.knowledge_base.chunks)}")

        try:
            await idle()
        finally:
            await self.client.stop()

    def run(self) -> None:
        self.client.run(self._serve())
