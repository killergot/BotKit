from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.lexicon.lexicon import LEXICON_RU


def get_users_keyboard(
    users: list,
    page: int = 0,
    per_page: int = 5,
    page_prefix: str = "users_page",
) -> InlineKeyboardMarkup:
    """Пагинированная клавиатура выбора пользователя."""
    builder = InlineKeyboardBuilder()

    start = page * per_page
    end = start + per_page
    page_users = users[start:end]

    for user in page_users:
        user_id = getattr(user, "id", None) or user.get("id")
        username_val = getattr(user, "username", None) or user.get("username")
        username = f"@{username_val}" if username_val else "Без username"
        button_text = f"{username} ({user_id})"
        builder.button(text=button_text, callback_data=f"select_user:{user_id}")

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад", callback_data=f"{page_prefix}:{page - 1}"
            )
        )
    if end < len(users):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ▶️", callback_data=f"{page_prefix}:{page + 1}"
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text=LEXICON_RU["cancel_btn"], callback_data="cancel_send_private")
    )
    builder.adjust(1)

    return builder.as_markup()


def get_cancel_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены для рассылки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LEXICON_RU["cancel_btn"], callback_data="cancel_broadcast")]
        ]
    )


def get_cancel_private_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены для личного сообщения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LEXICON_RU["cancel_btn"], callback_data="cancel_send_private")]
        ]
    )

