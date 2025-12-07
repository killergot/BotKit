from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.lexicon.lexicon_admin import LEXICON_COMMANDS_RU as ADMIN_COMMANDS_RU
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineRepository import MedicineRepository
from app.utils.flags import Flags
from app.database.psql import config
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


def _format_admin_help() -> str:
    text = "✔ *Admin commands:*"
    for cmd, desc in ADMIN_COMMANDS_RU.items():
        text += f"\n*{cmd}* : {desc}"
    return text


@router.message(Command('check_not_verify'))
async def cmd_check_not_verify(message: Message, db_session: AsyncSession):
    """Admin command: list unverified medicines and allow verification."""
    # Only allow configured admin
    try:
        admin_id = int(config.tg_bot.ID_admin)
    except Exception:
        await message.answer("Admin not configured")
        return

    if message.from_user.id != admin_id:
        await message.answer(LEXICON_RU.get('/help', 'Доступ запрещён'))
        return

    med_repo = MedicineRepository(db_session)
    meds = await med_repo.get_all(verified=False)

    if not meds:
        await message.answer("✅ Неверефицированных лекарств не найдено")
        return

    # build text and keyboard
    text = "🔎 Неверефицированные лекарства:\n\n"
    builder = InlineKeyboardBuilder()
    for med in meds:
        line = f"{med.id}. {med.name}"
        if med.dosage:
            line += f" ({med.dosage})"
        line += f" — {med.medicine_type.value}, {med.category.value}\n"
        text += line
        builder.button(text=f"Верифицировать: {med.name}", callback_data=f"admin_verify_med:{med.id}")

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith('admin_verify_med:'))
async def admin_verify_med(callback: CallbackQuery, db_session: AsyncSession):
    try:
        admin_id = int(config.tg_bot.ID_admin)
    except Exception:
        await callback.answer("Admin not configured", show_alert=True)
        return

    if callback.from_user.id != admin_id:
        await callback.answer("Доступ запрещён", show_alert=True)
        return

    med_id = int(callback.data.split(':', 1)[1])
    med_repo = MedicineRepository(db_session)
    med = await med_repo.get(med_id)
    if not med:
        await callback.answer("Лекарство не найдено", show_alert=True)
        return

    current_flags = getattr(med, 'flags', 0) or 0
    flags = Flags.from_int(current_flags)
    flags.set(Flags.VERIFIED)

    updated = await med_repo.update(med_id, flags=int(flags))
    if updated:
        await callback.message.edit_text(f"✅ Лекарство '{med.name}' помечено как верифицированное")
        await callback.answer("Верифицировано")
    else:
        await callback.answer("Ошибка при записи", show_alert=True)
