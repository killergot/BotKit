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

    for item in all_items[:5]:  # Показываем первые 5
        result_text += f"💊 {item.medicine.name}"
        if item.medicine.dosage:
            result_text += f" ({item.medicine.dosage})"
        result_text += f"\n   {item.quantity} {item.unit}"
        if item.expiry_date:
            result_text += f" | Годен до: {item.expiry_date.strftime('%d.%m.%Y')}"
        result_text += f"\n   📦 {item.medicine_kit.name}\n\n"

    if len(all_items) > 5:
        result_text += f"\n... и еще {len(all_items) - 5}"

    await callback.message.edit_text(result_text)
    await callback.answer()


@router.callback_query(F.data == "cancel_search")
async def cancel_search(callback: CallbackQuery):
    """Отмена поиска"""
    await callback.message.delete()
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

    # Показываем результаты
    result_text = LEXICON_RU['search_results'].format(query=query)

    for item in all_items:
        item_info = LEXICON_RU['search_item_info'].format(
            name=item.medicine.name,
            type=item.medicine.medicine_type.value,
            category=item.medicine.category.value,
            dosage=item.medicine.dosage or '-',
            quantity=item.quantity,
            unit=item.unit,
            expiry=item.expiry_date.strftime('%d.%m.%Y') if item.expiry_date else '-',
            location=item.location or '-',
            kit_name=item.medicine_kit.name
        )
        result_text += item_info + "\n"

    await message.answer(result_text)