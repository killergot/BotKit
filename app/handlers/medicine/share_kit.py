import uuid
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboard.medicine_kb import (
    get_share_kit_keyboard,
    get_share_request_keyboard
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.user_repository import UserRepository
from app.states.medicine import ShareKitStates

router = Router()

# Временное хранилище запросов (в production лучше использовать Redis или БД)
share_requests = {}


@router.message(Command("share"))
async def cmd_share(message: Message, state: FSMContext, db_session: AsyncSession):
    """Начало процесса шаринга аптечки"""
    user_id = message.from_user.id

    # Получаем аптечки пользователя
    kit_repo = MedicineKitRepository(db_session)
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        await message.answer(LEXICON_RU['share_no_kits'])
        return

    await message.answer(
        LEXICON_RU['share_choose_kit'],
        reply_markup=get_share_kit_keyboard(kits)
    )
    await state.set_state(ShareKitStates.choosing_kit)


@router.callback_query(ShareKitStates.choosing_kit, F.data.startswith("share_kit:"))
async def process_share_kit_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Выбор аптечки для шаринга"""
    kit_id = int(callback.data.split(":")[1])

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if not kit:
        await callback.answer("Аптечка не найдена", show_alert=True)
        return

    await state.update_data(share_kit_id=kit.id, share_kit_name=kit.name)

    await callback.message.edit_text(LEXICON_RU['share_enter_username'])
    await state.set_state(ShareKitStates.entering_username)
    await callback.answer()


@router.message(ShareKitStates.entering_username, F.text)
async def process_share_username(message: Message, state: FSMContext, db_session: AsyncSession):
    """Ввод username для шаринга"""
    username = message.text.strip().lstrip('@')
    user_id = message.from_user.id
    from_username = message.from_user.username or str(user_id)

    # Поиск пользователя по username
    user_repo = UserRepository(db_session)
    users = await user_repo.get_all()
    target_user = None

    for user in users:
        if user.username and user.username.lower() == username.lower():
            target_user = user
            break

    if not target_user:
        await message.answer(LEXICON_RU['share_user_not_found'].format(username=username))
        await state.clear()
        return

    # Проверка на шаринг самому себе
    if target_user.id == user_id:
        await message.answer(LEXICON_RU['share_self_error'])
        await state.clear()
        return

    # Проверка, не расшарена ли уже аптечка этому пользователю
    data = await state.get_data()
    kit_id = data['share_kit_id']

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if target_user in kit.users:
        await message.answer(LEXICON_RU['share_already_shared'])
        await state.clear()
        return

    # Создаем запрос на шаринг
    request_id = str(uuid.uuid4())
    share_requests[request_id] = {
        'from_user_id': user_id,
        'from_username': from_username,
        'to_user_id': target_user.id,
        'kit_id': kit_id,
        'kit_name': data['share_kit_name']
    }

    # Отправляем запрос целевому пользователю
    from aiogram import Bot
    bot: Bot = message.bot

    try:
        await bot.send_message(
            chat_id=target_user.id,
            text=LEXICON_RU['share_request_received'].format(
                from_username=from_username,
                kit_name=data['share_kit_name']
            ),
            reply_markup=get_share_request_keyboard(request_id)
        )

        await message.answer(
            LEXICON_RU['share_request_sent'].format(
                kit_name=data['share_kit_name'],
                username=username
            )
        )
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить запрос: {e}")

    await state.clear()


@router.callback_query(F.data.startswith("accept_share:"))
async def process_accept_share(callback: CallbackQuery, db_session: AsyncSession):
    """Принятие запроса на шаринг"""
    request_id = callback.data.split(":")[1]

    if request_id not in share_requests:
        await callback.answer("Запрос устарел", show_alert=True)
        await callback.message.delete()
        return

    request = share_requests[request_id]

    # Добавляем пользователя к аптечке
    kit_repo = MedicineKitRepository(db_session)
    success = await kit_repo.add_user(request['kit_id'], request['to_user_id'])

    if not success:
        await callback.answer("Ошибка при добавлении", show_alert=True)
        return

    # Обновляем название аптечки для нового пользователя
    kit = await kit_repo.get(request['kit_id'])
    new_name = f"{kit.name} (@{request['from_username']})"

    # На самом деле название аптечки общее для всех, поэтому просто уведомляем
    await callback.message.edit_text(
        LEXICON_RU['share_accepted'].format(kit_name=kit.name)
    )

    # Уведомляем отправителя
    try:
        await callback.bot.send_message(
            chat_id=request['from_user_id'],
            text=LEXICON_RU['share_confirmed'].format(
                username=callback.from_user.username or str(request['to_user_id']),
                kit_name=kit.name
            )
        )
    except:
        pass

    # Удаляем запрос
    del share_requests[request_id]
    await callback.answer("✅ Принято!")


@router.callback_query(F.data.startswith("decline_share:"))
async def process_decline_share(callback: CallbackQuery):
    """Отклонение запроса на шаринг"""
    request_id = callback.data.split(":")[1]

    if request_id in share_requests:
        request = share_requests[request_id]

        # Уведомляем отправителя об отклонении
        try:
            await callback.bot.send_message(
                chat_id=request['from_user_id'],
                text=f"❌ Пользователь @{callback.from_user.username or request['to_user_id']} отклонил запрос на доступ к аптечке \"{request['kit_name']}\""
            )
        except:
            pass

        del share_requests[request_id]

    await callback.message.edit_text(LEXICON_RU['share_declined'])
    await callback.answer()


@router.callback_query(ShareKitStates.choosing_kit, F.data == "cancel")
async def cancel_share(callback: CallbackQuery, state: FSMContext):
    """Отмена шаринга"""
    await callback.message.edit_text(LEXICON_RU['share_cancelled'])
    await state.clear()
    await callback.answer()