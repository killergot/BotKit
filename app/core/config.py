from dataclasses import dataclass
from environs import Env

from logging import getLogger
logger = getLogger(__name__)


@dataclass
class TgBot:
    token: str
    ID_admin: int


@dataclass
class DB:
    name: str
    host: str
    user: str
    password: str


@dataclass
class RedisConfig:
    host: str
    port: int
    password: str | None
    db: int


@dataclass
class Config:
    database: DB
    tg_bot: TgBot
    redis: RedisConfig
    mode: str  # Добавим режим работы


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)

    mode = env('MODE', 'dev')  # По умолчанию dev
    logger.warning(f"MODE: {mode}")

    # Выбираем хост БД в зависимости от режима
    if mode == 'dev':
        db_host = env('DB_HOST_DEV')
        redis_host = env('REDIS_HOST_DEV', 'localhost')
        db_pass = env('DB_PASS', '<PASSWORD>')
    else:
        db_host = env('DB_HOST_PROD')
        redis_host = env('REDIS_HOST_PROD', 'redis')
        db_pass = env('DB_PASS_PROD', '<PASSWORD>')

    return Config(
        mode=mode,
        tg_bot=TgBot(
            token=env('BOT_TOKEN'),
            ID_admin=int(env('ID_ADMIN'))
        ),
        database=DB(
            name=env('DB_NAME'),
            host=db_host,
            user=env('DB_USER'),
            password=db_pass
        ),
        redis=RedisConfig(
            host=redis_host,
            port=int(env('REDIS_PORT', 6379)),
            password=env('REDIS_PASSWORD', None),  # None если не задан
            db=int(env('REDIS_DB', 0))
        )
    )