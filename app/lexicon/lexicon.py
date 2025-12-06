
LEXICON_COMMANDS_RU: dict[str, str] = {
    '/help': 'Список команд',
}


LEXICON_RU: dict[str, str| dict[str,str]] = {
    '/start': 'Салам пополам плебей. Не знаешь что делать? '
              'Тыкай на /help',
    '/help' : f'{LEXICON_COMMANDS_RU}',
    'fail_tried_create_user': f'Не получилось создать пользователя, попробуйте позже'
}
