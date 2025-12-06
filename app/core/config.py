from dataclasses import dataclass
from environs import Env


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
class Config:
    database: DB
    tg_bot: TgBot


def load_config(path: str | None = None) -> Config:
    env = Env()
    env.read_env(path)
    db_host:str = None
    if env('MODE') == 'dev':
        db_host = env('DB_HOST_DEV')
    else:
        db_host = env('DB_HOST_PROD')

    return Config(tg_bot=TgBot(token=env('BOT_TOKEN'),
                               ID_admin=int(env('ID_ADMIN'))),
                  database=DB(name=env('DB_NAME'),
                              host=db_host,
                              user=env('DB_USER'),
                              password=str(env('DB_PASS')))
                  )

