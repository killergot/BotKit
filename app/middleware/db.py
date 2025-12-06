from aiogram import BaseMiddleware
from typing import Callable, Dict, Any

from aiogram.types import TelegramObject
from app.database.psql import AsyncSessionLocal


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            data["db_session"] = session
            return await handler(event, data)
