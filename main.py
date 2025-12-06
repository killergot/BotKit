import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.core.config import Config, load_config
from app.handlers import router
from app.keyboard.menu import set_main_menu
from app.middleware.db import DbSessionMiddleware
from app.middleware.redis import RedisMiddleware
from app.middleware.user import UserCheckMiddleware

logger = logging.getLogger(__name__)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')
    # Загружаем конфиг в переменную config
    config: Config = load_config()

    logger.info(f"Starting bot in {config.mode} mode")
    logger.info(f"Database host: {config.database.host}")
    logger.info(f"Redis host: {config.redis.host}")

    redis = Redis(
        host=config.redis.host,
        port=config.redis.port,
        password=config.redis.password if config.mode == 'prod' else None,
        db=config.redis.db,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_keepalive=True,
    )

    try:
        await redis.ping()
        logger.info("✅ Redis connected successfully")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        sys.exit(1)

    storage = RedisStorage(redis=redis)

    # Инициализируем бот и диспетчер
    bot = Bot(token=config.tg_bot.token)
    dp = Dispatcher(storage=storage)
    dp.message.middleware(DbSessionMiddleware())
    dp.message.middleware(UserCheckMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(UserCheckMiddleware())
    dp.callback_query.middleware(RedisMiddleware(redis))
    # Регистриуем роутеры в диспетчере
    dp.include_router(router)

    await set_main_menu(bot)

    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        # Закрываем соединения
        await redis.close()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())