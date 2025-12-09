from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.medicine import MedicineCategory
from app.keyboard.medicine_kb import (
    get_category_search_keyboard,
    get_medicine_items_keyboard
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.MedicineItemRepository import MedicineItemRepository

router = Router()


@router.message(Command("find"))
async def cmd_find(message: Message):
    """Поиск по категории"""
    await message.answer(
        LEXICON_RU['find_choose_category'],
        reply_markup=get_category_search_keyboard()
    )


@router.callback_query(F.data.startswith("find_category:"))
async def process_category_search(callback: CallbackQuery, db_session: AsyncSession):
    """Обработка выбора категории"""
    category_name = callback.data.split(":")[1]
    category = MedicineCategory[category_name]
    user_id = callback.from_user.id

    # Получаем аптечки пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await callback.answer("У вас нет аптечек", show_alert=True)
        return

    # Собираем все экземпляры нужной категории из всех аптечек пользователя
    item_repo = MedicineItemRepository(db_session)
    all_items = []

    for kit in kits:
        items = await item_repo.get_by_kit(kit.id)
        # Фильтруем по категории
        category_items = [item for item in items if item.medicine.category == category]
        all_items.extend(category_items)

    if not all_items:
        await callback.message.edit_text(LEXICON_RU['find_no_results'])
        await callback.answer()
        return


    # Формируем текст результатов
    result_text = LEXICON_RU['find_results'].format(count=len(all_items))

    # Используем унифицированную клавиатуру с префиксом для пагинации
    await callback.message.edit_text(
        result_text,
        reply_markup=get_medicine_items_keyboard(all_items, action="view", page=0, page_prefix=f"search_page_category:{category_name}")
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_search")
async def cancel_search(callback: CallbackQuery):
    """Отмена поиска"""
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("search_page_category:"))
async def search_page_category_callback(callback: CallbackQuery, db_session: AsyncSession):
    """Обработка пагинации для поиска по категории"""
    try:
        parts = callback.data.split(":")
        category_name = parts[1]
        page = int(parts[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка при обработке запроса", show_alert=True)
        return

    category = MedicineCategory[category_name]
    user_id = callback.from_user.id

    # Получаем аптечки пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await callback.answer("У вас нет аптечек", show_alert=True)
        return

    # Собираем все экземпляры нужной категории из всех аптечек пользователя
    item_repo = MedicineItemRepository(db_session)
    all_items = []

    for kit in kits:
        items = await item_repo.get_by_kit(kit.id)
        # Фильтруем по категории
        category_items = [item for item in items if item.medicine.category == category]
        all_items.extend(category_items)

    if not all_items:
        await callback.message.edit_text(LEXICON_RU['find_no_results'])
        await callback.answer()
        return

    # Формируем текст результатов
    result_text = LEXICON_RU['find_results'].format(count=len(all_items))

    # Используем унифицированную клавиатуру
    await callback.message.edit_text(
        result_text,
        reply_markup=get_medicine_items_keyboard(all_items, action="view", page=page, page_prefix=f"search_page_category:{category_name}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("search_page_name:"))
async def search_page_name_callback(callback: CallbackQuery, db_session: AsyncSession):
    """Обработка пагинации для поиска по имени"""
    try:
        # Извлекаем query и page из callback_data
        # Формат: search_page_name:{query}:{page}
        # Разбираем с конца, так как query может содержать двоеточия
        data = callback.data
        # Убираем префикс "search_page_name:"
        rest = data[len("search_page_name:"):]
        # Последнее двоеточие разделяет query и page
        last_colon = rest.rfind(":")
        if last_colon == -1:
            raise ValueError("Invalid callback data format")
        query = rest[:last_colon]
        page = int(rest[last_colon + 1:])
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

    # Ищем по всем аптечкам
    item_repo = MedicineItemRepository(db_session)
    all_items = []

    for kit in kits:
        items = await item_repo.search_in_kit(kit.id, query)
        all_items.extend(items)

    if not all_items:
        await callback.message.edit_text(LEXICON_RU['search_no_results'].format(query=query))
        await callback.answer()
        return

    # Показываем результаты с унифицированной клавиатурой
    result_text = LEXICON_RU['search_results'].format(query=query)
    await callback.message.edit_text(
        result_text,
        reply_markup=get_medicine_items_keyboard(all_items, action="view", page=page, page_prefix=f"search_page_name:{query}")
    )
    await callback.answer()


@router.message(F.text & ~F.text.startswith('/'))
async def search_by_name(message: Message, db_session: AsyncSession):
    """Поиск по названию лекарства в личном сообщении"""
    query = message.text.strip()
    user_id = message.from_user.id

    # Получаем аптечки пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        return  # Молча игнорируем если нет аптечек

    # Ищем по всем аптечкам
    item_repo = MedicineItemRepository(db_session)
    all_items = []

    for kit in kits:
        items = await item_repo.search_in_kit(kit.id, query)
        all_items.extend(items)

    if not all_items:
        await message.answer(LEXICON_RU['search_no_results'].format(query=query))
        return

    # Показываем результаты с унифицированной клавиатурой с префиксом для пагинации
    result_text = LEXICON_RU['search_results'].format(query=query)
    await message.answer(
        result_text,
        reply_markup=get_medicine_items_keyboard(all_items, action="view", page=0, page_prefix=f"search_page_name:{query}")
    )