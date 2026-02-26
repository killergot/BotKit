REMINDER_LEXICON_RU: dict[str, str] = {
    # Список
    "list_title": "🔔 Ваши напоминания ({count}):\n",
    "list_empty": "🔔 У вас пока нет напоминаний.\n\nНажмите «Добавить», чтобы создать первое.",
    "list_item": "{idx}. {text} (каждые {days} дн.)\n",
    "list_item_one_time": "{idx}. {text} (однократно)\n",

    # Детали
    "detail": (
        "🔔 Напоминание #{id}\n\n"
        "📝 Текст: {text}\n"
        "🔁 Интервал: {interval}\n"
        "📅 Следующее: {next_fire}\n"
        "📆 Создано: {created_at}"
    ),
    "interval_repeating": "каждые {days} дн.",
    "interval_one_time": "однократно",

    # Создание
    "create_enter_text": "📝 Введите текст напоминания:",
    "create_enter_interval": "🔢 Введите интервал в днях (целое число > 0):",
    "create_choose_type": "🔁 Выберите тип напоминания:",
    "create_confirm": (
        "✅ Проверьте напоминание:\n\n"
        "📝 Текст: {text}\n"
        "🔁 Тип: {type}\n"
        "🔢 Интервал: {interval} дн.\n"
        "📅 Первое срабатывание: ~через {interval} дн. в 09:00\n\n"
        "Сохранить?"
    ),
    "create_success": "✅ Напоминание создано!",
    "create_cancelled": "❌ Создание напоминания отменено.",

    # Редактирование
    "edit_choose_field": "✏️ Что изменить?",
    "edit_enter_text": "📝 Введите новый текст напоминания:",
    "edit_enter_interval": "🔢 Введите новый интервал в днях (целое число > 0):",
    "edit_success": "✅ Напоминание обновлено!",

    # Удаление
    "delete_confirm": "⚠️ Удалить напоминание?\n\n📝 {text}",
    "delete_success": "✅ Напоминание удалено.",
    "delete_cancelled": "❌ Удаление отменено.",

    # Валидация
    "error_invalid_interval": "❌ Введите целое число больше 0.",
    "error_text_empty": "❌ Текст не может быть пустым.",
    "error_not_found": "❌ Напоминание не найдено.",

    # Уведомление
    "notification": "🔔 Напоминание:\n\n{text}",

    # Кнопки
    "btn_add": "➕ Добавить",
    "btn_edit": "✏️ Редактировать",
    "btn_delete": "🗑 Удалить",
    "btn_back": "◀️ Назад",
    "btn_save": "✅ Сохранить",
    "btn_cancel": "❌ Отмена",
    "btn_repeating": "🔁 Повторяющееся",
    "btn_one_time": "1️⃣ Однократное",
    "btn_edit_text": "📝 Текст",
    "btn_edit_interval": "🔢 Интервал",
    "btn_confirm_delete": "⚠️ Да, удалить",
    "btn_close": "❌ Закрыть",
}
