from aiogram import Router, Bot, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from functools import lru_cache

from sqlalchemy.testing.config import test_schema

from app.lexicon.lexicon import LEXICON_RU, LEXICON_COMMANDS_RU
from app.keyboard.keyboard import kb_main
from app.repositoryes.user_repository import UserRepository


router = Router()

def format_help():
    formatted = "✔ *Список команд:*\n"
    for i, lesson in LEXICON_COMMANDS_RU.items():
        formatted += (
            f"\n*{i}* : {lesson}"
        )
    return formatted

async def send_format_help(message: Message):
    await message.answer(format_help(),
                         parse_mode=ParseMode.MARKDOWN,)

@router.message(CommandStart())
async def command_start(message: Message,
                  db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    user = await user_repo.get(message.from_user.id)
    if not user:
        user = await user_repo.create(message.from_user.id,
                                      message.from_user.username)
        if not user:
            await message.answer(text=LEXICON_RU['fail_tried_create_user'])
        await send_format_help(message)
    else:
        await message.answer(text=LEXICON_RU[message.text])

@router.message(Command('help'))
async def command_help(message: Message):
    await send_format_help(message)