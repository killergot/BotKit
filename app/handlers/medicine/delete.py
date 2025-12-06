from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboard.medicine_kb import (
    get_user_items_keyboard,
    get_confirm_delete_item_keyboard
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.MedicineItemRepository import MedicineItemRepository

router = Router()


class DeleteItemStates(StatesGroup):
    """Состояния для удаления item"""
    choosing_item = State()


@router.message(Command("del"))
async def cmd_delete_item(message: Message, state: FSMContext, db_session: AsyncSession):
    """Удаление item"""
    user_id = message.from_user.id

    # Получаем все items пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await message.answer(LEXICON_RU['delete_no_kits'])
        return

    # Собираем все items
    item_repo = MedicineItemRepository(db_session)
    all_items = []

    for kit in kits:
        items = await item_repo.get_by_kit(kit.id)
        all_items.extend(items)

    if not all_items:
        await message.answer(LEXICON_RU['delete_no_items'])
        return

    await message.answer(
        LEXICON_RU['delete_choose_item'],
        reply_markup=get_user_items_keyboard(all_items, action="delete")
    )
    await state.set_state(DeleteItemStates.choosing_item)


@router.callback_query(DeleteItemStates.choosing_item, F.data.startswith("delete_item:"))
async def confirm_delete_item(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Подтверждение удаления item"""
    item_id = int(callback.data.split(":")[1])

    item_repo = MedicineItemRepository(db_session)
    item = await item_repo.get(item_id)

    if not item:
        await callback.answer("Лекарство не найдено", show_alert=True)
        return

    await state.update_data(item_id=item_id)

    info = LEXICON_RU['delete_confirm'].format(
        name=item.medicine.name,
        dosage=item.medicine.dosage or '-',
        quantity=item.quantity,
        unit=item.unit,
        kit_name=item.medicine_kit.name
    )

    await callback.message.edit_text(
        info,
        reply_markup=get_confirm_delete_item_keyboard(item_id)
    )
    await callback.answer()


@router.callback_query(DeleteItemStates.choosing_item, F.data.startswith("confirm_delete_item:"))
async def process_delete_item(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Удаление item"""
    item_id = int(callback.data.split(":")[1])

    item_repo = MedicineItemRepository(db_session)
    item = await item_repo.get(item_id)

    if not item:
        await callback.answer("Лекарство не найдено", show_alert=True)
        return

    medicine_name = item.medicine.name

    success = await item_repo.delete(item_id)

    if success:
        await callback.message.edit_text(
            LEXICON_RU['delete_success'].format(name=medicine_name)
        )
        await state.clear()
        await callback.answer("✅ Удалено")
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)


@router.callback_query(DeleteItemStates.choosing_item, F.data.startswith("cancel_delete_item:"))
async def cancel_delete_item(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления"""
    await callback.message.edit_text(LEXICON_RU['delete_cancelled'])
    await state.clear()
    await callback.answer()