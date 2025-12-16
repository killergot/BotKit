from aiogram import Router, F, Bot
from aiogram.filters import Command, Filter
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.lexicon.lexicon_admin import (
    LEXICON_COMMANDS_RU as ADMIN_COMMANDS_RU,
    LEXICON_RU as ADMIN_LEXICON_RU,
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineRepository import MedicineRepository
from app.repositoryes.user_repository import UserRepository
from app.utils.flags import Flags
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.keyboard.admin_kb import (
    get_users_keyboard,
    get_cancel_broadcast_keyboard,
    get_cancel_private_keyboard,
)
from app.states.admin import BroadcastStates, PrivateMessageStates
from app.core.config import load_config

config = load_config()

class IsAdmin(Filter):
    def __init__(self):
        self.admin_id = config.tg_bot.ID_admin

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == self.admin_id


router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _get_pending_medicines(db_session: AsyncSession):
    """Лекарства, которые ещё не проверены и не верифицированы."""
    med_repo = MedicineRepository(db_session)
    meds = await med_repo.get_all(verified=False)

    filtered = []
    for med in meds:
        flags = Flags.from_int(getattr(med, "flags", 0))
        if flags.has(Flags.VERIFIED) or flags.has(Flags.CHECKED):
            continue
        filtered.append(med)
    return filtered


def _paginate(items: list, page: int, per_page: int = 5):
    start = page * per_page
    end = start + per_page
    return items[start:end], start, end


async def _render_pending_list_with_page(message, meds, page: int):
    if not meds:
        await message.edit_text(ADMIN_LEXICON_RU['no_pending_meds'])
        return

    page_items, start, end = _paginate(meds, page)

    text = ADMIN_LEXICON_RU['pending_list_title']
    builder = InlineKeyboardBuilder()
    for med in page_items:
        line = f"{med.id}. {med.name}"
        if med.dosage:
            line += f" ({med.dosage})"
        line += f" — {med.medicine_type.value}, {med.category.value}\n"
        text += line
        builder.button(text=f"{med.name}", callback_data=f"admin_view_med:{med.id}:{page}")

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text=ADMIN_LEXICON_RU['pagination_prev'], callback_data=f"admin_list_page:{page - 1}")
        )
    if end < len(meds):
        nav_buttons.append(
            InlineKeyboardButton(text=ADMIN_LEXICON_RU['pagination_next'], callback_data=f"admin_list_page:{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    await message.edit_text(text, reply_markup=builder.as_markup())


async def _render_pending_list(message, db_session: AsyncSession):
    """Показывает список непроверенных/неверифицированных лекарств."""
    meds = await _get_pending_medicines(db_session)
    await _render_pending_list_with_page(message, meds, page=0)


def _medicine_info_text(med) -> str:
    dosage = med.dosage or "-"
    notes = med.notes or "-"
    return (
        f"💊 {med.name}\n"
        f"🏷 {med.medicine_type.value} / {med.category.value}\n"
        f"💉 Дозировка: {dosage}\n"
        f"📝 Заметки: {notes}"
    )


async def _render_pending_list(message, db_session: AsyncSession):
    """Показывает список непроверенных/неверифицированных лекарств."""
    meds = await _get_pending_medicines(db_session)
    if not meds:
        await message.edit_text("✅ Неверефицированных лекарств не найдено")
        return

    text = "🔎 Неверефицированные лекарства:\n\n"
    builder = InlineKeyboardBuilder()
    for med in meds:
        line = f"{med.id}. {med.name}"
        if med.dosage:
            line += f" ({med.dosage})"
        line += f" — {med.medicine_type.value}, {med.category.value}\n"
        text += line
        builder.button(text=f"{med.name}", callback_data=f"admin_view_med:{med.id}:0")

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    await message.edit_text(text, reply_markup=builder.as_markup())


def _format_admin_help() -> str:
    text = "✔ *Admin commands:*"
    for cmd, desc in ADMIN_COMMANDS_RU.items():
        text += f"\n*{cmd}* : {desc}"
    return text


@router.message(Command('check_not_verify'))
async def cmd_check_not_verify(message: Message, db_session: AsyncSession):
    """Admin command: list unverified medicines and allow verification."""
    meds = await _get_pending_medicines(db_session)

    if not meds:
        await message.answer(ADMIN_LEXICON_RU['no_pending_meds'])
        return

    text = ADMIN_LEXICON_RU['pending_list_title']
    page_items, start, end = _paginate(meds, page=0)
    builder = InlineKeyboardBuilder()

    for med in page_items:
        line = f"{med.id}. {med.name}"
        if med.dosage:
            line += f" ({med.dosage})"
        line += f" — {med.medicine_type.value}, {med.category.value}\n"
        text += line
        builder.button(text=f"{med.name}", callback_data=f"admin_view_med:{med.id}")

    nav_buttons = []
    if end < len(meds):
        nav_buttons.append(
            InlineKeyboardButton(text=ADMIN_LEXICON_RU['pagination_next'], callback_data=f"admin_list_page:{1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin_list_page:"))
async def admin_list_page(callback: CallbackQuery, db_session: AsyncSession):
    """Пагинация списка непроверенных лекарств."""
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(ADMIN_LEXICON_RU['pagination_error'], show_alert=True)
        return

    meds = await _get_pending_medicines(db_session)
    await _render_pending_list_with_page(callback.message, meds, page)
    await callback.answer()


@router.callback_query(F.data.startswith('admin_view_med:'))
async def admin_view_med(callback: CallbackQuery, db_session: AsyncSession):
    """Показать детали лекарства с кнопками действий."""
    parts = callback.data.split(':')
    med_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0
    med_repo = MedicineRepository(db_session)
    med = await med_repo.get(med_id)
    if not med:
        await callback.answer(ADMIN_LEXICON_RU['med_not_found'], show_alert=True)
        return

    flags = Flags.from_int(getattr(med, "flags", 0))
    # Если уже обработано, вернёмся к списку
    if flags.has(Flags.VERIFIED) or flags.has(Flags.CHECKED):
        await callback.answer(ADMIN_LEXICON_RU['already_processed'], show_alert=True)
        meds = await _get_pending_medicines(db_session)
        await _render_pending_list_with_page(callback.message, meds, page)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Верифицировать", callback_data=f"admin_verify_med:{med.id}:{page}")
    builder.button(text="❌ Отклонить", callback_data=f"admin_reject_med:{med.id}:{page}")
    builder.button(text=ADMIN_LEXICON_RU['pagination_prev'], callback_data=f"admin_back_to_list:{page}")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    await callback.message.edit_text(
        ADMIN_LEXICON_RU['med_info'].format(
            name=med.name,
            type=med.medicine_type.value,
            category=med.category.value,
            dosage=med.dosage or "-",
            notes=med.notes or "-",
        ),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_back_to_list:"))
async def admin_back_to_list(callback: CallbackQuery, db_session: AsyncSession):
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer(ADMIN_LEXICON_RU['pagination_error'], show_alert=True)
        return
    meds = await _get_pending_medicines(db_session)
    await _render_pending_list_with_page(callback.message, meds, page)
    await callback.answer()


@router.callback_query(F.data.startswith('admin_verify_med:'))
async def admin_verify_med(callback: CallbackQuery, db_session: AsyncSession):

    parts = callback.data.split(':')
    med_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0
    med_repo = MedicineRepository(db_session)
    med = await med_repo.get(med_id)
    if not med:
        await callback.answer(ADMIN_LEXICON_RU['med_not_found'], show_alert=True)
        return

    current_flags = getattr(med, 'flags', 0) or 0
    flags = Flags.from_int(current_flags)
    flags.set(Flags.CHECKED)
    flags.set(Flags.VERIFIED)

    updated = await med_repo.update(med_id, flags=int(flags))
    if updated:
        await callback.message.edit_text(ADMIN_LEXICON_RU['verify_success'].format(name=med.name))
        await callback.answer(ADMIN_LEXICON_RU['verify_answer'])
    else:
        await callback.answer(ADMIN_LEXICON_RU['reject_error'], show_alert=True)


@router.callback_query(F.data.startswith('admin_reject_med:'))
async def admin_reject_med(callback: CallbackQuery, db_session: AsyncSession):
    parts = callback.data.split(':')
    med_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0
    med_repo = MedicineRepository(db_session)
    med = await med_repo.get(med_id)
    if not med:
        await callback.answer(ADMIN_LEXICON_RU['med_not_found'], show_alert=True)
        return

    current_flags = getattr(med, 'flags', 0) or 0
    flags = Flags.from_int(current_flags)
    flags.set(Flags.CHECKED)
    flags.clear(Flags.VERIFIED)

    updated = await med_repo.update(med_id, flags=int(flags))
    if updated:
        await callback.message.edit_text(ADMIN_LEXICON_RU['reject_success'].format(name=med.name))
        await callback.answer(ADMIN_LEXICON_RU['reject_answer'])
    else:
        await callback.answer(ADMIN_LEXICON_RU['reject_error'], show_alert=True)


@router.callback_query(F.data == "cancel")
async def cancel_admin_flow(callback: CallbackQuery,
                            state: FSMContext,):
    try:
        await callback.message.delete()
        await state.clear()
        await callback.answer()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer(ADMIN_LEXICON_RU['cancelled'])


# -------------------- Broadcast -------------------- #
@router.message(Command('broadcast'))
async def start_broadcast(message: Message, state: FSMContext, db_session: AsyncSession):

    user_repo = UserRepository(db_session)
    users = await user_repo.get_all()
    if not users:
        await message.answer(LEXICON_RU["broadcast_no_users"])
        return

    await state.set_state(BroadcastStates.waiting_message)
    await message.answer(
        LEXICON_RU["broadcast_prompt"],
        reply_markup=get_cancel_broadcast_keyboard(),
    )


@router.message(BroadcastStates.waiting_message, Command("cancel"))
async def cancel_broadcast_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(LEXICON_RU["broadcast_cancelled"])


@router.callback_query(F.data == "cancel_broadcast")
async def cancel_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(LEXICON_RU["broadcast_cancelled"])
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def process_broadcast(message: Message, bot: Bot, state: FSMContext, db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    users = await user_repo.get_all()
    if not users:
        await message.answer(LEXICON_RU["broadcast_no_users"])
        await state.clear()
        return

    sent = 0
    for user in users:
        try:
            await bot.send_message(chat_id=user.id, text=message.text)
            sent += 1
        except Exception:
            # Игнорируем неуспешные отправки (бот заблокирован и т.п.)
            continue

    await state.clear()
    await message.answer(LEXICON_RU["broadcast_done"].format(count=sent))


# -------------------- Send private -------------------- #
@router.message(Command('send_private'))
async def start_private_message(message: Message, state: FSMContext, db_session: AsyncSession):
    user_repo = UserRepository(db_session)
    users = await user_repo.get_all()
    if not users:
        await message.answer(LEXICON_RU["private_no_users"])
        return

    users_data = [{"id": u.id, "username": u.username} for u in users]
    await state.update_data(users=users_data)
    await state.set_state(PrivateMessageStates.choosing_user)

    await message.answer(
        LEXICON_RU["private_choose_user"],
        reply_markup=get_users_keyboard(users_data),
    )


@router.callback_query(PrivateMessageStates.choosing_user, F.data.startswith("users_page:"))
async def paginate_users(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = data.get("users", [])
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Ошибка пагинации", show_alert=True)
        return

    await callback.message.edit_reply_markup(
        reply_markup=get_users_keyboard(users, page=page)
    )
    await callback.answer()


@router.callback_query(PrivateMessageStates.choosing_user, F.data.startswith("select_user:"))
async def select_user(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    users = data.get("users", [])
    try:
        user_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Неверные данные пользователя", show_alert=True)
        return

    target = next((u for u in users if u.get("id") == user_id), None)
    if not target:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await state.update_data(target_user=target)
    await state.set_state(PrivateMessageStates.waiting_message)
    username = target.get("username")
    username_display = f"@{username}" if username else "пользователю без username"

    await callback.message.edit_text(
        LEXICON_RU["private_enter_message"].format(
            username_display=username_display, user_id=target.get("id")
        ),
        reply_markup=get_cancel_private_keyboard(),
    )
    await callback.answer()


@router.message(PrivateMessageStates.waiting_message, Command("cancel"))
async def cancel_private_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(LEXICON_RU["private_cancelled"])


@router.callback_query(F.data == "cancel_send_private")
async def cancel_private_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(LEXICON_RU["private_cancelled"])
    await callback.answer()


@router.message(PrivateMessageStates.waiting_message)
async def send_private(message: Message, bot: Bot, state: FSMContext):
    data = await state.get_data()
    target = data.get("target_user")
    if not target:
        await message.answer("Пользователь не выбран, начните заново командой /send_private")
        await state.clear()
        return

    try:
        await bot.send_message(chat_id=target.get("id"), text=message.text)
        username = target.get("username")
        username_display = f"@{username}" if username else f"ID {target.get('id')}"
        await message.answer(
            LEXICON_RU["private_sent"].format(username_display=username_display)
        )
    except Exception:
        await message.answer(LEXICON_RU["private_failed"])

    await state.clear()
