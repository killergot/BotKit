LEXICON_COMMANDS_RU: dict[str, str] = {
    '/check_not_verify' : 'Проверить подозрительные лекарства',
    '/help': 'Список команд',
    '/upload': 'Добавить лекарство',
    '/my_kits': 'Мои аптечки',
    '/delete_kits': 'Удаление аптечки/ корзина аптечек',
    '/find': 'Поиск по категории',
    '/expired': 'Просроченные лекарства',
    '/share': 'Поделиться аптечкой',
    '/update': 'Обновить лекарство',
    '/del': 'Удалить лекарство',
    '/broadcast': 'Рассылка сообщения всем пользователям',
    '/crons' : 'Напоминания',
    '/send_private': 'Личное сообщение пользователю',
}

# Тексты, используемые в админских сценариях
LEXICON_RU: dict[str, str] = {
    'no_pending_meds': '✅ Неверефицированных лекарств не найдено',
    'pending_list_title': '🔎 Неверефицированные лекарства:\n\n',
    'med_info': '💊 {name}\n'
                '🏷 {type} / {category}\n'
                '💉 Дозировка: {dosage}\n'
                '📝 Заметки: {notes}',
    'already_processed': 'Это лекарство уже обработано',
    'verify_success': '✅ Лекарство "{name}" помечено как верифицированное',
    'verify_answer': 'Верифицировано',
    'reject_success': '❌ Лекарство "{name}" отмечено как отклонённое',
    'reject_error': 'Ошибка при записи',
    'reject_answer': 'Отклонено',
    'med_not_found': 'Лекарство не найдено',
    'pagination_error': 'Ошибка пагинации',
    'cancelled': 'Отменено',
    'pagination_prev': '◀️ Назад',
    'pagination_next': 'Вперед ▶️',
}