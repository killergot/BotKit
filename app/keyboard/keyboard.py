from aiogram.types import KeyboardButton,ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardButton,InlineKeyboardMarkup

kb_main = ReplyKeyboardMarkup(keyboard=[[
        KeyboardButton(text='/help')]],
        resize_keyboard=True
)

ikb: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text='❤️',callback_data='like'),
        InlineKeyboardButton(text='👎🏾',callback_data='dislike')],
                     [InlineKeyboardButton(text='Другое фото',callback_data='Другое фото')],
                     [InlineKeyboardButton(text='Главное меню',callback_data='Главное меню')]])

def create_inline_kb(temp : list) -> InlineKeyboardMarkup:
    keyboard : list[list[InlineKeyboardButton]] = [[],[],[],[],[]]
    counter = 1
    for i in temp:
        keyboard[counter // 8].append(InlineKeyboardButton(text=i,callback_data=i))
        counter+=1

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
