from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis


class RedisMiddleware(BaseMiddleware):
    """Middleware для добавления Redis в хендлеры"""

    def __init__(self, redis: Redis):
        self.redis = redis
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        data['redis'] = self.redis
        return await handler(event, data)