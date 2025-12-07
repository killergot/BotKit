from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models.medicine import MedicineType, MedicineCategory, Medicine, MedicineKit


def get_medicine_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора типа лекарства"""
    builder = InlineKeyboardBuilder()

    for medicine_type in MedicineType:
        builder.button(
            text=medicine_type.value,
            callback_data=f"medicine_type:{medicine_type.name}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)  # 2 кнопки в ряд

    return builder.as_markup()


def get_medicine_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора категории лекарства"""
    builder = InlineKeyboardBuilder()

    for category in MedicineCategory:
        builder.button(
            text=category.value,
            callback_data=f"medicine_category:{category.name}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(2)  # 2 кнопки в ряд

    return builder.as_markup()


def get_skip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой пропуска"""
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data="skip")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Сохранить", callback_data="confirm_save")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    return builder.as_markup()


def get_medicine_kit_keyboard(kits: list) -> InlineKeyboardMarkup:
    """Клавиатура для выбора аптечки"""
    builder = InlineKeyboardBuilder()

    for kit in kits:
        builder.button(
            text=kit.name,
            callback_data=f"select_kit:{kit.id}"
        )

    builder.button(text="➕ Создать новую", callback_data="create_new_kit")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    return builder.as_markup()


def get_similar_medicines_keyboard(medicines: list[Medicine]) -> InlineKeyboardMarkup:
    """Клавиатура для выбора похожего лекарства"""
    builder = InlineKeyboardBuilder()

    for medicine in medicines:
        # Формируем текст кнопки с информацией о лекарстве
        button_text = f"{medicine.name}"
        if medicine.dosage:
            button_text += f" ({medicine.dosage})"

        builder.button(
            text=button_text,
            callback_data=f"select_medicine:{medicine.id}"
        )

    builder.button(text="➕ Создать новое", callback_data="create_new_medicine")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    return builder.as_markup()

def get_category_search_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора категории при поиске"""
    builder = InlineKeyboardBuilder()

    for category in MedicineCategory:
        builder.button(
            text=category.value,
            callback_data=f"find_category:{category.name}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel_search")
    builder.adjust(2)

    return builder.as_markup()


def get_medicine_items_keyboard(items: list, page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура со списком найденных экземпляров лекарств"""
    builder = InlineKeyboardBuilder()

    start = page * per_page
    end = start + per_page
    page_items = items[start:end]

    for item in page_items:
        button_text = f"💊 {item.medicine.name}"
        if item.medicine.dosage:
            button_text += f" ({item.medicine.dosage})"
        button_text += f" - {item.quantity} {item.unit}"

        builder.button(
            text=button_text,
            callback_data=f"view_item:{item.id}"
        )

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"page:{page - 1}"))
    if end < len(items):
        nav_buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"page:{page + 1}"))

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close"))
    builder.adjust(1)

    return builder.as_markup()


def get_share_kit_keyboard(kits: list[MedicineKit]) -> InlineKeyboardMarkup:
    """Клавиатура для выбора аптечки для шаринга"""
    builder = InlineKeyboardBuilder()

    for kit in kits:
        builder.button(
            text=kit.name,
            callback_data=f"share_kit:{kit.id}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)

    return builder.as_markup()


def get_share_request_keyboard(request_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для принятия/отклонения запроса на шаринг"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Принять", callback_data=f"accept_share:{request_id}")
    builder.button(text="❌ Отклонить", callback_data=f"decline_share:{request_id}")
    builder.adjust(2)

    return builder.as_markup()


def get_user_kits_keyboard(kits: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком аптечек пользователя"""
    builder = InlineKeyboardBuilder()

    for kit in kits:
        builder.button(
            text=f"Удалить: {kit.name}",
            callback_data=f"delete_kit:{kit.id}"
        )

    builder.adjust(1)
    return builder.as_markup()


def get_confirm_delete_keyboard(kit_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления аптечки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"confirm_delete_kit:{kit_id}")
    builder.button(text="❌ Отмена", callback_data=f"cancel_delete_kit:{kit_id}")
    builder.adjust(1)
    return builder.as_markup()


def get_user_items_keyboard(items: list, action: str = "update") -> InlineKeyboardMarkup:
    """Клавиатура со списком items пользователя"""
    builder = InlineKeyboardBuilder()

    for item in items:
        button_text = f"💊 {item.medicine.name}"
        if item.medicine.dosage:
            button_text += f" ({item.medicine.dosage})"
        button_text += f" - {item.quantity} {item.unit}"

        builder.button(
            text=button_text,
            callback_data=f"{action}_item:{item.id}"
        )

    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_update_field_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора поля для обновления"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔢 Количество", callback_data="update_field:quantity")
    builder.button(text="📍 Местоположение", callback_data="update_field:location")
    builder.button(text="📝 Заметки", callback_data="update_field:notes")
    builder.button(text="❌ Отмена", callback_data="cancel")
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_update")
    return builder.as_markup()


def get_confirm_delete_item_keyboard(item_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления item"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"confirm_delete_item:{item_id}")
    builder.button(text="❌ Отмена", callback_data=f"cancel_delete_item:{item_id}")
    builder.adjust(1)
    return builder.as_markup()