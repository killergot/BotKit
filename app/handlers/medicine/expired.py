from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

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

    for item in all_expired:
        item_text = LEXICON_RU['expired_item'].format(
            name=item.medicine.name,
            dosage=item.medicine.dosage or '-',
            expiry=item.expiry_date.strftime('%d.%m.%Y'),
            quantity=item.quantity,
            unit=item.unit,
            kit_name=item.medicine_kit.name
        )
        result_text += item_text + "\n"

    await message.answer(result_text)