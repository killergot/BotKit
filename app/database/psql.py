from sqlalchemy import false
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.engine import URL
from app.core.config import load_config


config = load_config()

DATABASE_URL = URL.create(
    'postgresql+asyncpg',
    username=config.database.user,
    password=config.database.password,
    host=config.database.host,
    port=5432,
    database=config.database.name,
)

engine = create_async_engine(DATABASE_URL, echo=False,)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
