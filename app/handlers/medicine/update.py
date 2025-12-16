import decimal
from decimal import Decimal
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboard.medicine_kb import (
    get_medicine_items_keyboard,
    get_update_field_keyboard,
    get_cancel_keyboard
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.MedicineItemRepository import MedicineItemRepository

router = Router()


class UpdateItemStates(StatesGroup):
    """Состояния для обновления item"""
    choosing_item = State()
    choosing_field = State()
    entering_new_value = State()


@router.message(Command("update"))
async def cmd_update(message: Message, state: FSMContext, db_session: AsyncSession):
    """Обновление item"""
    user_id = message.from_user.id

    # Получаем все items пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await message.answer(LEXICON_RU['update_no_kits'])
        return

    # Собираем все items
    item_repo = MedicineItemRepository(db_session)
    all_items = []

    for kit in kits:
        items = await item_repo.get_by_kit(kit.id)
        all_items.extend(items)

    if not all_items:
        await message.answer(LEXICON_RU['update_no_items'])
        return

    await message.answer(
        LEXICON_RU['update_choose_item'],
        reply_markup=get_medicine_items_keyboard(
            all_items,
            action="view",
            page=0,
            per_page=10,
            page_prefix="update_page"
        )
    )


@router.callback_query(F.data.startswith("update_page:"))
async def update_page_callback(callback: CallbackQuery, db_session: AsyncSession):
    """Пагинация списка лекарств для команды /update"""
    try:
        _, page_str = callback.data.split(":")
        page = int(page_str)
    except Exception:
        await callback.answer()
        return

    user_id = callback.from_user.id

    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await callback.message.edit_text(LEXICON_RU['update_no_kits'])
        await callback.answer()
        return

    item_repo = MedicineItemRepository(db_session)
    all_items = []
    for kit in kits:
        items = await item_repo.get_by_kit(kit.id)
        all_items.extend(items)

    if not all_items:
        await callback.message.edit_text(LEXICON_RU['update_no_items'])
        await callback.answer()
        return

    await callback.message.edit_text(
        LEXICON_RU['update_choose_item'],
        reply_markup=get_medicine_items_keyboard(
            all_items,
            action="view",
            page=page,
            per_page=10,
            page_prefix="update_page"
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("update_item:"))
async def process_item_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Выбор item для обновления"""
    item_id = int(callback.data.split(":")[1])

    item_repo = MedicineItemRepository(db_session)
    item = await item_repo.get(item_id)

    if not item:
        await callback.answer("Лекарство не найдено", show_alert=True)
        return

    await state.update_data(item_id=item_id)

    # Показываем текущие данные и выбор поля
    current_info = LEXICON_RU['update_current_info'].format(
        name=item.medicine.name,
        quantity=item.quantity,
        unit=item.unit,
        location=item.location or '-',
        notes=item.notes or '-'
    )

    await callback.message.edit_text(
        current_info,
        reply_markup=get_update_field_keyboard()
    )
    await state.set_state(UpdateItemStates.choosing_field)
    await callback.answer()


@router.callback_query(UpdateItemStates.choosing_field, F.data.startswith("update_field:"))
async def process_field_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Выбор поля для обновления"""
    field = callback.data.split(":")[1]

    await state.update_data(update_field=field)

    # Получаем текущий item, чтобы показать старое значение
    data = await state.get_data()
    item_id = data['item_id']

    item_repo = MedicineItemRepository(db_session)
    item = await item_repo.get(item_id)

    # Сообщения для каждого поля
    prompts = {
        'quantity': LEXICON_RU['update_enter_quantity'],
        'location': LEXICON_RU['update_enter_location'],
        'notes': LEXICON_RU['update_enter_notes']
    }

    base_prompt = prompts.get(field, "Введите новое значение:")

    # Добавляем текущее значение к тексту подсказки
    if field == 'quantity':
        current = f"{item.quantity} {item.unit}"
    elif field == 'location':
        current = item.location or '-'
    elif field == 'notes':
        current = item.notes or '-'
    else:
        current = '-'

    text = f"{base_prompt}\n\nСейчас: <b>{current}</b>"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(UpdateItemStates.entering_new_value)
    await callback.answer()


@router.message(UpdateItemStates.entering_new_value, F.text)
async def process_new_value(message: Message, state: FSMContext, db_session: AsyncSession):
    """Ввод нового значения"""
    data = await state.get_data()
    item_id = data['item_id']
    field = data['update_field']
    new_value = message.text.strip()

    item_repo = MedicineItemRepository(db_session)

    try:
        # Получаем текущее значение для отображения "до/после"
        item = await item_repo.get(item_id)

        # Валидация и обновление в зависимости от поля
        if field == 'quantity':
            quantity = Decimal(new_value.replace(',', '.'))
            if quantity < 0:
                raise ValueError
            await item_repo.update(item_id, quantity=str(quantity))
            old_value = f"{item.quantity} {item.unit}"
            new_value_pretty = f"{quantity} {item.unit}"
        elif field == 'location':
            old_value = item.location or '-'
            await item_repo.update(item_id, location=new_value)
            new_value_pretty = new_value or '-'
        elif field == 'notes':
            old_value = item.notes or '-'
            await item_repo.update(item_id, notes=new_value)
            new_value_pretty = new_value or '-'
        else:
            old_value = "-"
            new_value_pretty = new_value or "-"

        # Показываем старое и новое значение
        await message.answer(
            f"{LEXICON_RU['update_success']}\n\n"
            f"🔄 Было: <b>{old_value}</b>\n"
            f"✅ Стало: <b>{new_value_pretty}</b>"
        )
        await state.clear()

    except (ValueError, decimal.InvalidOperation):
        await message.answer(LEXICON_RU['error_invalid_number'])


@router.callback_query(UpdateItemStates.entering_new_value, F.data == "cancel_update")
async def cancel_update(callback: CallbackQuery, state: FSMContext):
    """Отмена обновления"""
    await callback.message.edit_text(LEXICON_RU['update_cancelled'])
    await state.clear()
    await callback.answer()