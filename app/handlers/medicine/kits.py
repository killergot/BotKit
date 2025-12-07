from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboard.medicine_kb import (
    get_user_kits_keyboard,
    get_confirm_delete_keyboard,
    get_trash_kits_keyboard,
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository

router = Router()


@router.message(Command("my_kits"))
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