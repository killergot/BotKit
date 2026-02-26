from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.admin import IsAdmin
from app.lexicon.lexicon_reminder import REMINDER_LEXICON_RU as L
from app.repositoryes.ReminderRepository import ReminderRepository
from app.states.reminder import ReminderCreateStates, ReminderEditStates
from app.keyboard.reminder_kb import (
    get_reminders_list_keyboard,
    get_reminder_detail_keyboard,
    get_reminder_type_keyboard,
    get_confirm_create_keyboard,
    get_edit_field_keyboard,
    get_confirm_delete_keyboard,
    get_cancel_keyboard,
)

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# -------------------- Helpers -------------------- #

async def _show_list(message, db_session: AsyncSession, user_id: int, edit: bool = True):
    repo = ReminderRepository(db_session)
    reminders = await repo.get_by_user(user_id)

    if not reminders:
        text = L["list_empty"]
    else:
        text = L["list_title"].format(count=len(reminders))
        for idx, r in enumerate(reminders, 1):
            if r.is_one_time:
                text += L["list_item_one_time"].format(idx=idx, text=r.text[:40])
            else:
                text += L["list_item"].format(idx=idx, text=r.text[:40], days=r.interval_days)

    kb = get_reminders_list_keyboard(reminders)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# -------------------- Command /crons -------------------- #

@router.message(Command("crons"))
async def cmd_crons(message: Message, db_session: AsyncSession, state: FSMContext):
    await state.clear()
    await _show_list(message, db_session, message.from_user.id, edit=False)


# -------------------- View detail -------------------- #

@router.callback_query(F.data.startswith("cron_view:"))
async def cron_view(callback: CallbackQuery, db_session: AsyncSession):
    reminder_id = int(callback.data.split(":")[1])
    repo = ReminderRepository(db_session)
    r = await repo.get(reminder_id)
    if not r:
        await callback.answer(L["error_not_found"], show_alert=True)
        return

    interval_text = (
        L["interval_one_time"] if r.is_one_time
        else L["interval_repeating"].format(days=r.interval_days)
    )
    text = L["detail"].format(
        id=r.id,
        text=r.text,
        interval=interval_text,
        next_fire=r.next_fire_at.strftime("%d.%m.%Y %H:%M"),
        created_at=r.created_at.strftime("%d.%m.%Y %H:%M"),
    )
    await callback.message.edit_text(text, reply_markup=get_reminder_detail_keyboard(r.id))
    await callback.answer()


@router.callback_query(F.data == "cron_back_list")
async def cron_back_list(callback: CallbackQuery, db_session: AsyncSession):
    await _show_list(callback.message, db_session, callback.from_user.id)
    await callback.answer()


# -------------------- Create (FSM) -------------------- #

@router.callback_query(F.data == "cron_add")
async def cron_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReminderCreateStates.entering_text)
    await callback.message.edit_text(L["create_enter_text"], reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(ReminderCreateStates.entering_text)
async def cron_create_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer(L["error_text_empty"])
        return
    await state.update_data(text=text)
    await state.set_state(ReminderCreateStates.entering_interval)
    await message.answer(L["create_enter_interval"], reply_markup=get_cancel_keyboard())


@router.message(ReminderCreateStates.entering_interval)
async def cron_create_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text.strip())
        if interval <= 0:
            raise ValueError
    except ValueError:
        await message.answer(L["error_invalid_interval"])
        return

    await state.update_data(interval_days=interval)
    await state.set_state(ReminderCreateStates.choosing_type)
    await message.answer(L["create_choose_type"], reply_markup=get_reminder_type_keyboard())


@router.callback_query(ReminderCreateStates.choosing_type, F.data.startswith("cron_type:"))
async def cron_create_type(callback: CallbackQuery, state: FSMContext):
    type_val = callback.data.split(":")[1]
    is_one_time = type_val == "one_time"
    await state.update_data(is_one_time=is_one_time)

    data = await state.get_data()
    type_label = L["btn_one_time"] if is_one_time else L["btn_repeating"]
    text = L["create_confirm"].format(
        text=data["text"],
        type=type_label,
        interval=data["interval_days"],
    )
    await callback.message.edit_text(text, reply_markup=get_confirm_create_keyboard())
    await callback.answer()


@router.callback_query(F.data == "cron_save")
async def cron_save(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    data = await state.get_data()
    if "text" not in data:
        await callback.answer(L["create_cancelled"], show_alert=True)
        await state.clear()
        return

    repo = ReminderRepository(db_session)
    await repo.create(
        user_id=callback.from_user.id,
        text=data["text"],
        interval_days=data["interval_days"],
        is_one_time=data.get("is_one_time", False),
    )
    await state.clear()
    await callback.message.edit_text(L["create_success"])
    await callback.answer()


# -------------------- Edit (FSM) -------------------- #

@router.callback_query(F.data.startswith("cron_edit:"))
async def cron_edit(callback: CallbackQuery, state: FSMContext):
    reminder_id = int(callback.data.split(":")[1])
    await state.set_state(ReminderEditStates.choosing_field)
    await state.update_data(edit_reminder_id=reminder_id)
    await callback.message.edit_text(
        L["edit_choose_field"],
        reply_markup=get_edit_field_keyboard(reminder_id),
    )
    await callback.answer()


@router.callback_query(ReminderEditStates.choosing_field, F.data.startswith("cron_edit_text:"))
async def cron_edit_text_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReminderEditStates.entering_text)
    await callback.message.edit_text(L["edit_enter_text"], reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(ReminderEditStates.entering_text)
async def cron_edit_text_done(message: Message, state: FSMContext, db_session: AsyncSession):
    text = message.text.strip()
    if not text:
        await message.answer(L["error_text_empty"])
        return

    data = await state.get_data()
    repo = ReminderRepository(db_session)
    result = await repo.update(data["edit_reminder_id"], text=text)
    await state.clear()

    if result:
        await message.answer(L["edit_success"])
    else:
        await message.answer(L["error_not_found"])


@router.callback_query(ReminderEditStates.choosing_field, F.data.startswith("cron_edit_interval:"))
async def cron_edit_interval_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReminderEditStates.entering_interval)
    await callback.message.edit_text(L["edit_enter_interval"], reply_markup=get_cancel_keyboard())
    await callback.answer()


@router.message(ReminderEditStates.entering_interval)
async def cron_edit_interval_done(message: Message, state: FSMContext, db_session: AsyncSession):
    try:
        interval = int(message.text.strip())
        if interval <= 0:
            raise ValueError
    except ValueError:
        await message.answer(L["error_invalid_interval"])
        return

    data = await state.get_data()
    repo = ReminderRepository(db_session)
    result = await repo.update(data["edit_reminder_id"], interval_days=interval)
    await state.clear()

    if result:
        await message.answer(L["edit_success"])
    else:
        await message.answer(L["error_not_found"])


# -------------------- Delete -------------------- #

@router.callback_query(F.data.startswith("cron_delete:"))
async def cron_delete(callback: CallbackQuery, db_session: AsyncSession):
    reminder_id = int(callback.data.split(":")[1])
    repo = ReminderRepository(db_session)
    r = await repo.get(reminder_id)
    if not r:
        await callback.answer(L["error_not_found"], show_alert=True)
        return

    await callback.message.edit_text(
        L["delete_confirm"].format(text=r.text),
        reply_markup=get_confirm_delete_keyboard(r.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cron_confirm_delete:"))
async def cron_confirm_delete(callback: CallbackQuery, db_session: AsyncSession):
    reminder_id = int(callback.data.split(":")[1])
    repo = ReminderRepository(db_session)
    deleted = await repo.delete(reminder_id)

    if deleted:
        await callback.message.edit_text(L["delete_success"])
    else:
        await callback.answer(L["error_not_found"], show_alert=True)
    await callback.answer()


# -------------------- Cancel / Close -------------------- #

@router.callback_query(F.data == "cron_cancel")
async def cron_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(L["create_cancelled"])
    await callback.answer()


@router.callback_query(F.data == "cron_close")
async def cron_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
