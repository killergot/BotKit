from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models.medicine import MedicineType, MedicineCategory, Medicine


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