from typing import Callable, Dict, Any, Optional

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositoryes.user_repository import UserRepository


class UserCheckMiddleware(BaseMiddleware):
    def __init__(self, create_if_missing: bool = False):
        self.create_if_missing = create_if_missing

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Expect DbSessionMiddleware to set `db_session` in data
        db_session: Optional[AsyncSession] = data.get("db_session")
        if db_session is None:
            return await handler(event, data)

        user_id = None
        username = None

        if isinstance(event, Message):
            if event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username
        elif isinstance(event, CallbackQuery):
            if event.from_user:
                user_id = event.from_user.id
                username = event.from_user.username

        # If we couldn't determine user id, continue
        if user_id is None:
            return await handler(event, data)

        # Allow /start command to pass so the CommandStart handler can create the user
        if isinstance(event, Message) and event.text:
            first_token = event.text.strip().split()[0].lower()
            if first_token.startswith('/start'):
                return await handler(event, data)

        user_repo = UserRepository(db_session)
        user = await user_repo.get(user_id)

        if not user:
            if self.create_if_missing:
                await user_repo.create(user_id, username)
            else:
                # If not creating, try to notify and stop processing
                bot = data.get("bot")
                if bot:
                    try:
                        await bot.send_message(chat_id=user_id, text="Вы не зарегистрированы в системе. Отправьте /start.")
                    except Exception:
                        pass
                return

        return await handler(event, data)
