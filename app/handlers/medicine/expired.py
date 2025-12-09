from datetime import date

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboard.medicine_kb import get_medicine_items_keyboard
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.MedicineItemRepository import MedicineItemRepository

router = Router()


@router.message(Command("expired"))
async def cmd_expired(message: Message, db_session: AsyncSession):
    """Показать просроченные лекарства"""
    user_id = message.from_user.id

    # Получаем аптечки пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await message.answer("У вас нет аптечек")
        return

    # Собираем просроченные из всех аптечек
    item_repo = MedicineItemRepository(db_session)
    all_expired = []

    for kit in kits:
        expired = await item_repo.get_expired(kit.id)
        all_expired.extend(expired)

    if not all_expired:
        await message.answer(LEXICON_RU['expired_no_items'])
        return

    # Формируем список
    result_text = LEXICON_RU['expired_list']

    # Используем унифицированную клавиатуру
    await message.answer(
        result_text,
        reply_markup=get_medicine_items_keyboard(all_expired, action="view", page=0, page_prefix="expired_page")
    )


@router.callback_query(F.data.startswith("expired_page:"))
async def expired_page_callback(callback: CallbackQuery, db_session: AsyncSession):
    """Обработка пагинации для просроченных лекарств"""
    try:
        page = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка при обработке запроса", show_alert=True)
        return

    user_id = callback.from_user.id

    # Получаем аптечки пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await callback.answer("У вас нет аптечек", show_alert=True)
        return

    # Собираем просроченные из всех аптечек
    item_repo = MedicineItemRepository(db_session)
    all_expired = []

    for kit in kits:
        expired = await item_repo.get_expired(kit.id)
        all_expired.extend(expired)

    if not all_expired:
        await callback.message.edit_text(LEXICON_RU['expired_no_items'])
        await callback.answer()
        return

    # Формируем список
    result_text = LEXICON_RU['expired_list']

    # Используем унифицированную клавиатуру
    await callback.message.edit_text(
        result_text,
        reply_markup=get_medicine_items_keyboard(all_expired, action="view", page=page, page_prefix="expired_page")
    )
    await callback.answer()