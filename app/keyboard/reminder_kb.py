from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.lexicon.lexicon_reminder import REMINDER_LEXICON_RU as L


def get_reminders_list_keyboard(reminders) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in reminders:
        label = r.text[:30] + ("..." if len(r.text) > 30 else "")
        builder.button(text=label, callback_data=f"cron_view:{r.id}")
    builder.row(InlineKeyboardButton(text=L["btn_add"], callback_data="cron_add"))
    builder.row(InlineKeyboardButton(text=L["btn_close"], callback_data="cron_close"))
    builder.adjust(1)
    return builder.as_markup()


def get_reminder_detail_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=L["btn_edit"], callback_data=f"cron_edit:{reminder_id}")
    builder.button(text=L["btn_delete"], callback_data=f"cron_delete:{reminder_id}")
    builder.row(InlineKeyboardButton(text=L["btn_back"], callback_data="cron_back_list"))
    builder.adjust(2)
    return builder.as_markup()


def get_reminder_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=L["btn_repeating"], callback_data="cron_type:repeating")
    builder.button(text=L["btn_one_time"], callback_data="cron_type:one_time")
    builder.row(InlineKeyboardButton(text=L["btn_cancel"], callback_data="cron_cancel"))
    builder.adjust(2)
    return builder.as_markup()


def get_confirm_create_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=L["btn_save"], callback_data="cron_save")
    builder.button(text=L["btn_cancel"], callback_data="cron_cancel")
    builder.adjust(2)
    return builder.as_markup()


def get_edit_field_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=L["btn_edit_text"], callback_data=f"cron_edit_text:{reminder_id}")
    builder.button(text=L["btn_edit_interval"], callback_data=f"cron_edit_interval:{reminder_id}")
    builder.row(InlineKeyboardButton(text=L["btn_cancel"], callback_data="cron_cancel"))
    builder.adjust(2)
    return builder.as_markup()


def get_confirm_delete_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=L["btn_confirm_delete"], callback_data=f"cron_confirm_delete:{reminder_id}")
    builder.button(text=L["btn_cancel"], callback_data="cron_cancel")
    builder.adjust(2)
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=L["btn_cancel"], callback_data="cron_cancel")]
        ]
    )
