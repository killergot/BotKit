from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboard.medicine_kb import (
    get_user_kits_keyboard,
    get_confirm_delete_keyboard,
    get_trash_kits_keyboard,
    get_medicine_kit_keyboard,
    get_kit_items_keyboard,
    get_back_to_kit_keyboard,
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.MedicineItemRepository import MedicineItemRepository
from datetime import date

router = Router()


@router.message(Command("delete_kits"))
async def cmd_my_kits(message: Message, db_session: AsyncSession):
    """Показать список аптечек пользователя"""
    user_id = message.from_user.id

    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id=user_id,deleted=False)

    if not kits:
        await message.answer(LEXICON_RU['my_kits_empty'])
        return

    # Формируем текст со списком аптечек
    text = LEXICON_RU['my_kits_list'].format(count=len(kits))

    for i, kit in enumerate(kits, 1):
        items_count = len(kit.items)
        users_count = len(kit.users)

        text += f"\n{i}. 📦 {kit.name}"
        text += f"\n   💊 Лекарств: {items_count}"
        text += f"\n   👥 Пользователей: {users_count}"
        if kit.description:
            text += f"\n   📝 {kit.description}"
        text += "\n"

    await message.answer(text, reply_markup=get_user_kits_keyboard(kits))


@router.message(Command("my_kits"))
async def cmd_kits(message: Message, db_session: AsyncSession):
    """Показать список аптечек для просмотра содержимого"""
    user_id = message.from_user.id

    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id=user_id)

    if not kits:
        await message.answer(LEXICON_RU.get('my_kits_empty', 'У вас нет аптечек'))
        return

    text = LEXICON_RU.get('kits_list_header', 'Аптечки:')
    await message.answer(text, reply_markup=get_medicine_kit_keyboard(kits))


@router.callback_query(F.data.startswith("select_kit:"))
async def show_kit_items(callback: CallbackQuery, db_session: AsyncSession):
    """Показать список лекарств в выбранной аптечке (первый экран пагинации)"""
    kit_id = int(callback.data.split(":")[1])

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if not kit or kit.deleted:
        await callback.answer("Аптечка не найдена или удалена", show_alert=True)
        return

    # Доступ к атрибутам пока сессия активна
    kit_name = kit.name
    kit_id_val = kit.id
    items = list(kit.items) if kit.items else []
    
    # Принудительно загружаем medicine для каждого item, пока сессия активна
    for item in items:
        if item.medicine:
            _ = item.medicine.name
            _ = item.medicine.dosage

    # Формируем текст для первого экрана
    header = LEXICON_RU.get('kit_items_header', 'Аптечка "{name}" — лекарства ({count}):')
    text = header.format(name=kit_name, count=len(items))

    # Пагинация: показываем по 5 элементов
    per_page = 5

    await callback.message.edit_text(text, reply_markup=get_kit_items_keyboard(items, kit_id_val, page=0, per_page=per_page))
    await callback.answer()


@router.callback_query(F.data.startswith("kit_page:"))
async def kit_page_callback(callback: CallbackQuery, db_session: AsyncSession):
    """Обработка навигации по страницам в просмотре аптечки"""
    try:
        _, kit_id_str, page_str = callback.data.split(":")
        kit_id = int(kit_id_str)
        page = int(page_str)
    except Exception:
        await callback.answer()
        return

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if not kit or kit.deleted:
        await callback.answer("Аптечка не найдена или удалена", show_alert=True)
        return

    # Доступ к атрибутам пока сессия активна
    kit_name = kit.name
    kit_id_val = kit.id
    items = list(kit.items) if kit.items else []
    
    # Принудительно загружаем medicine для каждого item, пока сессия активна
    for item in items:
        if item.medicine:
            _ = item.medicine.name
            _ = item.medicine.dosage
    
    per_page = 5

    header = LEXICON_RU.get('kit_items_header', 'Аптечка "{name}" — лекарства ({count}):')
    text = header.format(name=kit_name, count=len(items))

    await callback.message.edit_text(text, reply_markup=get_kit_items_keyboard(items, kit_id_val, page=page, per_page=per_page))
    await callback.answer()



@router.callback_query(F.data == "show_trash_kits")
async def show_trash_kits(callback: CallbackQuery, db_session: AsyncSession):
    """Показать корзину с удалёнными аптечками пользователя"""
    user_id = callback.from_user.id

    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id, deleted=True)

    if not kits:
        await callback.message.edit_text(LEXICON_RU.get('my_kits_trash_empty', '🗑 У вас нет удалённых аптечек'))
        await callback.answer()
        return

    # Формируем текст со списком удалённых аптечек
    text = LEXICON_RU.get('my_kits_trash_list', '🗑 Удалённые аптечки ({count}):\n').format(count=len(kits))

    for i, kit in enumerate(kits, 1):
        items_count = len(kit.items)
        users_count = len(kit.users)

        text += f"\n{i}. 🗑 {kit.name}"
        text += f"\n   💊 Лекарств: {items_count}"
        text += f"\n   👥 Пользователей: {users_count}"
        if kit.description:
            text += f"\n   📝 {kit.description}"
        text += "\n"

    await callback.message.edit_text(text, reply_markup=get_trash_kits_keyboard(kits))
    await callback.answer()


@router.callback_query(F.data.startswith("restore_kit:"))
async def restore_kit(callback: CallbackQuery, db_session: AsyncSession):
    """Восстановление удалённой аптечки"""
    kit_id = int(callback.data.split(":")[1])

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if not kit:
        await callback.answer("Аптечка не найдена", show_alert=True)
        return

    kit_name = kit.name

    restored = await kit_repo.update(kit_id, deleted=False)

    if restored:
        await callback.message.edit_text(LEXICON_RU.get('my_kits_restored', '✅ Аптечка "{name}" восстановлена').format(name=kit_name))
        await callback.answer("✅ Восстановлено")
    else:
        await callback.answer("❌ Ошибка при восстановлении", show_alert=True)


@router.callback_query(F.data.startswith("delete_kit:"))
async def confirm_delete_kit(callback: CallbackQuery, db_session: AsyncSession):
    """Запрос подтверждения удаления аптечки"""
    kit_id = int(callback.data.split(":")[1])

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if not kit:
        await callback.answer("Аптечка не найдена", show_alert=True)
        return

    items_count = len(kit.items)

    await callback.message.edit_text(
        LEXICON_RU['my_kits_confirm_delete'].format(
            name=kit.name,
            items_count=items_count
        ),
        reply_markup=get_confirm_delete_keyboard(kit_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_kit:"))
async def process_delete_kit(callback: CallbackQuery, db_session: AsyncSession):
    """Удаление аптечки"""
    kit_id = int(callback.data.split(":")[1])

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if not kit:
        await callback.answer("Аптечка не найдена", show_alert=True)
        return

    kit_name = kit.name

    # Удаляем аптечку (items удалятся автоматически через cascade)
    success = await kit_repo.update(kit_id,
                                    deleted=True)

    if success:
        await callback.message.edit_text(
            LEXICON_RU['my_kits_deleted'].format(name=kit_name)
        )
        await callback.answer("✅ Удалено")
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


@router.callback_query(F.data.startswith("cancel_delete_kit:"))
async def cancel_delete_kit(callback: CallbackQuery, db_session: AsyncSession):
    """Отмена удаления"""
    await callback.message.edit_text(LEXICON_RU['my_kits_delete_cancelled'])
    await callback.answer()


@router.callback_query(F.data.startswith("view_item:"))
async def view_item_details(callback: CallbackQuery, db_session: AsyncSession):
    """Показать полную информацию о лекарстве"""
    try:
        item_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка при обработке запроса", show_alert=True)
        return

    item_repo = MedicineItemRepository(db_session)
    item = await item_repo.get(item_id)

    if not item:
        await callback.answer("Лекарство не найдено", show_alert=True)
        return

    # Доступ к атрибутам пока сессия активна
    medicine = item.medicine
    kit = item.medicine_kit
    
    medicine_name = medicine.name
    medicine_type = medicine.medicine_type.value if medicine.medicine_type else "Не указано"
    medicine_category = medicine.category.value if medicine.category else "Не указано"
    medicine_dosage = medicine.dosage or "Не указано"
    medicine_notes = medicine.notes or "Нет"
    
    item_quantity = item.quantity
    item_unit = item.unit
    item_expiry = item.expiry_date.strftime("%d.%m.%Y") if item.expiry_date else "Не указано"
    item_location = item.location or "Не указано"
    item_notes = item.notes or "Нет"
    kit_name = kit.name
    kit_id_val = kit.id

    # Определяем текущую страницу: находим позицию item в списке
    kit_repo = MedicineKitRepository(db_session)
    all_items = await kit_repo.get(kit_id_val)
    if all_items and all_items.items:
        items_list = list(all_items.items)
        per_page = 5
        try:
            item_index = next(i for i, it in enumerate(items_list) if it.id == item_id)
            page = item_index // per_page
        except StopIteration:
            page = 0
    else:
        page = 0

    # Формируем текст с полной информацией
    text = f"💊 *{medicine_name}*\n\n"
    text += f"🏷 *Тип:* {medicine_type}\n"
    text += f"📋 *Категория:* {medicine_category}\n"
    text += f"💉 *Дозировка:* {medicine_dosage}\n\n"
    text += f"🔢 *Количество:* {item_quantity} {item_unit}\n"
    text += f"📅 *Срок годности:* {item_expiry}\n"
    text += f"📍 *Местоположение:* {item_location}\n"
    text += f"📦 *Аптечка:* {kit_name}\n\n"
    
    if medicine_notes != "Нет":
        text += f"📝 *Заметки о лекарстве:*\n{medicine_notes}\n\n"
    
    if item_notes != "Нет":
        text += f"📝 *Заметки об экземпляре:*\n{item_notes}"

    await callback.message.edit_text(
        text,
        reply_markup=get_back_to_kit_keyboard(kit_id_val, page),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "close")
async def close_callback(callback: CallbackQuery):
    """Обработка закрытия просмотра"""
    await callback.message.delete()
    await callback.answer()