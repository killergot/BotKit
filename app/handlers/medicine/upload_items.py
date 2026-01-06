import decimal
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional, List

from logging import getLogger
logger = getLogger(__name__)

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from rapidfuzz import fuzz, process

from app.database.models.medicine import MedicineType, MedicineCategory, Medicine
from app.keyboard.medicine_kb import (
    get_medicine_enum_keyboard,
    get_skip_keyboard,
    get_confirm_upload_medical_keyboard,
    get_medicine_kit_keyboard,
    get_similar_medicines_keyboard,
    get_cancel_only_keyboard,
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.MedicineRepository import MedicineRepository
from app.repositoryes.MedicineItemRepository import MedicineItemRepository
from app.states.medicine import MedicineUploadStates
from app.utils.flags import Flags

router = Router()

# Минимальный процент совпадения для показа похожих лекарств
SIMILARITY_THRESHOLD = 60


async def _store_last_bot_message(state: FSMContext, sent_message: Message | None = None, *, callback_message: CallbackQuery | None = None):
    """Store last bot message id and text in FSM state for later editing."""
    if sent_message:
        await state.update_data(
            last_bot_message_id=sent_message.message_id,
            last_bot_message_text=sent_message.text or sent_message.html_text or '',
            last_bot_chat_id=sent_message.chat.id,
            last_bot_has_reply_markup=bool(sent_message.reply_markup)
        )
    elif callback_message:
        # callback_message is a CallbackQuery; use its message
        msg = callback_message.message
        await state.update_data(
            last_bot_message_id=msg.message_id,
            last_bot_message_text=msg.text or '',
            last_bot_chat_id=msg.chat.id,
            last_bot_has_reply_markup=bool(msg.reply_markup)
        )


async def _append_recommendation(state: FSMContext, bot, recommendation: str):
    """Append recommendation text to the last stored bot message. If editing fails, send as a new message."""
    data = await state.get_data()
    msg_id = data.get('last_bot_message_id')
    chat_id = data.get('last_bot_chat_id')
    text = data.get('last_bot_message_text', '')

    has_markup = data.get('last_bot_has_reply_markup', False)

    # If the last bot message had an inline keyboard, avoid editing it (that would remove the keyboard).
    if msg_id and chat_id and text is not None and not has_markup:
        new_text = text + "\n\n" + recommendation
        try:
            await bot.edit_message_text(new_text, chat_id=chat_id, message_id=msg_id)
            await state.update_data(last_bot_message_text=new_text)
            return
        except Exception:
            pass

    # Otherwise / fallback: send as a new message (so we don't lose keyboards)
    await bot.send_message(chat_id=chat_id or None, text=recommendation)


def _fits_numeric(value: Decimal, precision: int = 10, scale: int = 2) -> bool:
    """Check if Decimal fits into Numeric(precision, scale).

    We scale the value by 10**scale and check that the resulting integer
    has at most `precision` digits.
    """
    try:
        scaled = (value * (10 ** scale)).to_integral_value(rounding=ROUND_DOWN)
    except Exception:
        return False

    unscaled_abs = abs(int(scaled))
    return len(str(unscaled_abs)) <= precision



def find_similar_medicines(search_name: str, all_medicines: List[Medicine], limit: int = 3) -> List[
    tuple[Medicine, float]]:
    """
    Находит похожие лекарства с помощью RapidFuzz

    :param search_name: Название для поиска
    :param all_medicines: Список всех лекарств
    :param limit: Максимальное количество результатов
    :return: Список кортежей (Medicine, similarity_score)
    """
    if not all_medicines:
        return []

    # Создаем словарь {название: объект}
    medicine_dict = {med.name: med for med in all_medicines}

    # Ищем похожие названия
    results = process.extract(
        search_name,
        medicine_dict.keys(),
        scorer=fuzz.WRatio,
        limit=limit
    )

    # Фильтруем по порогу и возвращаем объекты Medicine
    similar = []
    for name, score, _ in results:
        if score >= SIMILARITY_THRESHOLD:
            similar.append((medicine_dict[name], score))

    return similar


@router.message(Command("upload"))
async def cmd_upload_start(message: Message,
                           state: FSMContext,
                           db_session: AsyncSession):
    """Начало процесса добавления лекарства"""
    user_id = message.from_user.id
    kit_repo = MedicineKitRepository(db_session)

    # Получаем аптечки пользователя
    kits = await kit_repo.get_by_user(user_id)

    if not kits:
        # Если нет аптечек, создаем первую
        sent = await message.answer(LEXICON_RU['upload_no_kits'])
        await _store_last_bot_message(state, sent_message=sent)
        await state.set_state(MedicineUploadStates.choosing_kit)
        await state.update_data(creating_first_kit=True)
    else:
        # Показываем список аптечек
        sent = await message.answer(
            LEXICON_RU['upload_start'],
            reply_markup=get_medicine_kit_keyboard(kits)
        )
        await _store_last_bot_message(state, sent_message=sent)
        await state.set_state(MedicineUploadStates.choosing_kit)


@router.message(MedicineUploadStates.choosing_kit, F.text)
async def process_kit_name(
        message: Message,
        state: FSMContext,
        db_session: AsyncSession
):
    """Создание новой аптечки"""
    user_id = message.from_user.id
    kit_name = message.text.strip()

    kit_repo = MedicineKitRepository(db_session)

    # Создаем аптечку
    kit = await kit_repo.create(name=kit_name, user_ids=[user_id])

    sent = await message.answer(LEXICON_RU['upload_kit_created'].format(name=kit.name))

    # Сохраняем ID аптечки и переходим к вводу названия лекарства
    await state.update_data(medicine_kit_id=kit.id, kit_name=kit.name)
    sent2 = await message.answer(
        LEXICON_RU['upload_enter_name'],
        reply_markup=get_cancel_only_keyboard(),
    )
    await _store_last_bot_message(state, sent_message=sent2)
    await state.set_state(MedicineUploadStates.entering_name)


@router.callback_query(MedicineUploadStates.choosing_kit, F.data.startswith("select_kit:"))
async def process_kit_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Выбор существующей аптечки"""
    kit_id = int(callback.data.split(":")[1])

    kit_repo = MedicineKitRepository(db_session)
    kit = await kit_repo.get(kit_id)

    if not kit:
        await callback.answer("Аптечка не найдена", show_alert=True)
        return

    await state.update_data(medicine_kit_id=kit.id, kit_name=kit.name)

    await callback.message.edit_text(
        LEXICON_RU['upload_enter_name'],
        reply_markup=get_cancel_only_keyboard(),
    )
    await state.set_state(MedicineUploadStates.entering_name)
    await callback.answer()


@router.callback_query(MedicineUploadStates.choosing_kit, F.data == "create_new_kit")
async def process_create_new_kit(callback: CallbackQuery, state: FSMContext):
    """Создание новой аптечки из меню выбора"""
    await callback.message.edit_text(LEXICON_RU['upload_no_kits'])
    await state.update_data(creating_new_kit=True)
    await callback.answer()


@router.message(MedicineUploadStates.entering_name, F.text)
async def process_medicine_name(message: Message, state: FSMContext, db_session: AsyncSession):
    """Ввод названия лекарства с поиском похожих"""
    name = message.text.strip()

    if not name:
        await message.answer(LEXICON_RU['error_empty_input'])
        return

    # Validate minimal name length
    if len(name) < 2:
        try:
            await message.delete()
        except Exception:
            pass
        await _append_recommendation(state, message.bot, LEXICON_RU['recommend_name_too_short'])
        return
    # Сохраняем введенное название
    await state.update_data(search_medicine_name=name)

    # Получаем все лекарства из базы
    medicine_repo = MedicineRepository(db_session)
    # Получаем только верифицированные лекарства для показа похожих
    all_medicines = await medicine_repo.get_all(verified=True)

    if all_medicines:
        # Ищем похожие
        similar = find_similar_medicines(name, all_medicines, limit=3)

        if similar:
            # Показываем похожие лекарства
            similar_text = "🔍 Найдены похожие лекарства:\n\n"
            for i, (med, score) in enumerate(similar, 1):
                similar_text += f"{i}. {med.name}"
                if med.dosage:
                    similar_text += f" ({med.dosage})"
                similar_text += f" - {med.medicine_type.value}, {med.category.value}"
                similar_text += "\n"
                similar_text += f"   Совпадение: {score:.0f}%\n\n"

            similar_text += "Выберите подходящее или создайте новое:"

            # Извлекаем только объекты Medicine
            medicines_only = [med for med, _ in similar]

            sent = await message.answer(
                similar_text,
                reply_markup=get_similar_medicines_keyboard(medicines_only)
            )
            await _store_last_bot_message(state, sent_message=sent)
            return

    # Если похожих не найдено, продолжаем создание нового
    await state.update_data(medicine_name=name)
    sent = await message.answer(
        LEXICON_RU['upload_choose_type'],
        reply_markup=get_medicine_enum_keyboard(MedicineType, 'medicine_type')
    )
    await _store_last_bot_message(state, sent_message=sent)
    await state.set_state(MedicineUploadStates.choosing_type)


@router.callback_query(MedicineUploadStates.entering_name, F.data.startswith("select_medicine:"))
async def process_select_existing_medicine(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Выбор существующего лекарства из похожих"""
    medicine_id = int(callback.data.split(":")[1])

    medicine_repo = MedicineRepository(db_session)
    medicine = await medicine_repo.get(medicine_id)

    if not medicine:
        await callback.answer("Лекарство не найдено", show_alert=True)
        return

    # Сохраняем выбранное лекарство
    await state.update_data(
        selected_medicine_id=medicine.id,
        medicine_name=medicine.name,
        medicine_type=medicine.medicine_type.name,  # Сохраняем name, не сам enum!
        medicine_category=medicine.category.name,  # Сохраняем name, не сам enum!
        medicine_dosage=medicine.dosage,
        medicine_notes=medicine.notes,
        using_existing_medicine=True
    )

    info_text = f"💊 Тип: {medicine.medicine_type.value}\n"
    info_text += f"🏷 Категория: {medicine.category.value}\n"
    if medicine.dosage:
        info_text += f"💉 Дозировка: {medicine.dosage}\n"

    await callback.message.edit_text(
        LEXICON_RU['upload_medicine_selected'].format(
            name=medicine.name,
            info=info_text
        )
    )

    # Переходим сразу к вводу данных об экземпляре
    await callback.message.answer(LEXICON_RU['upload_enter_quantity'])
    await state.set_state(MedicineUploadStates.entering_quantity)
    await callback.answer()


@router.callback_query(MedicineUploadStates.entering_name, F.data == "create_new_medicine")
async def process_create_new_medicine(callback: CallbackQuery, state: FSMContext):
    """Создание нового лекарства (пропуск выбора из похожих)"""
    data = await state.get_data()
    name = data.get('search_medicine_name', '')

    await state.update_data(medicine_name=name, using_existing_medicine=False)

    await callback.message.edit_text(
        LEXICON_RU['upload_choose_type'],
        reply_markup=get_medicine_enum_keyboard(MedicineType, 'medicine_type')
    )
    await _store_last_bot_message(state, callback_message=callback)
    await state.set_state(MedicineUploadStates.choosing_type)
    await callback.answer()


@router.callback_query(MedicineUploadStates.choosing_type, F.data.startswith("medicine_type:"))
async def process_medicine_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа лекарства"""
    type_name = callback.data.split(":")[1]

    await state.update_data(medicine_type=type_name)

    await callback.message.edit_text(
        LEXICON_RU['upload_choose_category'],
        reply_markup=get_medicine_enum_keyboard(MedicineCategory,
                                                'medicine_category')
    )
    await _store_last_bot_message(state, callback_message=callback)
    await state.set_state(MedicineUploadStates.choosing_category)
    await callback.answer()


@router.callback_query(MedicineUploadStates.choosing_category, F.data.startswith("medicine_category:"))
async def process_medicine_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории лекарства"""
    category_name = callback.data.split(":")[1]

    await state.update_data(medicine_category=category_name)

    await callback.message.edit_text(
        LEXICON_RU['upload_enter_dosage'],
        reply_markup=get_skip_keyboard()
    )
    await _store_last_bot_message(state, callback_message=callback)
    await state.set_state(MedicineUploadStates.entering_dosage)
    await callback.answer()


@router.message(MedicineUploadStates.entering_dosage, F.text)
async def process_dosage(message: Message, state: FSMContext):
    """Ввод дозировки"""
    dosage = message.text.strip()
    await state.update_data(medicine_dosage=dosage)

    sent = await message.answer(
        LEXICON_RU['upload_enter_medicine_notes'],
        reply_markup=get_skip_keyboard()
    )
    await _store_last_bot_message(state, sent_message=sent)
    await state.set_state(MedicineUploadStates.entering_medicine_notes)


@router.callback_query(MedicineUploadStates.entering_dosage, F.data == "skip")
async def skip_dosage(callback: CallbackQuery, state: FSMContext):
    """Пропуск дозировки"""
    await state.update_data(medicine_dosage=None)

    await callback.message.edit_text(
        LEXICON_RU['upload_enter_medicine_notes'],
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MedicineUploadStates.entering_medicine_notes)
    await callback.answer()


@router.message(MedicineUploadStates.entering_medicine_notes, F.text)
async def process_medicine_notes(message: Message, state: FSMContext):
    """Ввод заметок о лекарстве"""
    notes = message.text.strip()
    await state.update_data(medicine_notes=notes)

    sent = await message.answer(LEXICON_RU['upload_enter_quantity'])
    await _store_last_bot_message(state, sent_message=sent)
    await state.set_state(MedicineUploadStates.entering_quantity)


@router.callback_query(MedicineUploadStates.entering_medicine_notes, F.data == "skip")
async def skip_medicine_notes(callback: CallbackQuery, state: FSMContext):
    """Пропуск заметок о лекарстве"""
    await state.update_data(medicine_notes=None)

    await callback.message.edit_text(LEXICON_RU['upload_enter_quantity'])
    await state.set_state(MedicineUploadStates.entering_quantity)
    await callback.answer()


@router.message(MedicineUploadStates.entering_quantity, F.text)
async def process_quantity(message: Message, state: FSMContext):
    """Ввод количества"""
    try:
        quantity = Decimal(message.text.strip().replace(',', '.'))
        if quantity < 0:
            raise ValueError

        # Validate fits model Numeric(10,2)
        if not _fits_numeric(quantity, precision=10, scale=2):
            try:
                await message.delete()
            except Exception:
                pass
            await _append_recommendation(state, message.bot, LEXICON_RU['recommend_numeric_too_large'])
            return

        # Minimal allowed value
        min_val = Decimal('0.01')
        if quantity < min_val:
            try:
                await message.delete()
            except Exception:
                pass
            await _append_recommendation(state, message.bot, LEXICON_RU['recommend_min_quantity'])
            return

        # Сохраняем как строку!
        await state.update_data(item_quantity=str(quantity))
        sent = await message.answer(LEXICON_RU['upload_enter_unit'])
        await _store_last_bot_message(state, sent_message=sent)
        await state.set_state(MedicineUploadStates.entering_unit)

    except (ValueError, decimal.InvalidOperation):
        try:
            await message.delete()
        except Exception:
            pass
        await _append_recommendation(state, message.bot, LEXICON_RU['recommend_invalid_quantity'])


@router.message(MedicineUploadStates.entering_unit, F.text)
async def process_unit(message: Message, state: FSMContext):
    """Ввод единицы измерения"""
    unit = message.text.strip()

    if not unit:
        try:
            await message.delete()
        except Exception:
            pass
        await _append_recommendation(state, message.bot, LEXICON_RU['recommend_invalid_unit'])
        return

    # Validate unit length
    if len(unit) > 10:
        try:
            await message.delete()
        except Exception:
            pass
        await _append_recommendation(state, message.bot, LEXICON_RU['recommend_unit_too_long'])
        return

    await state.update_data(item_unit=unit)
    sent = await message.answer(
        LEXICON_RU['upload_enter_expiry_date'],
        reply_markup=get_skip_keyboard()
    )
    await _store_last_bot_message(state, sent_message=sent)
    await state.set_state(MedicineUploadStates.entering_expiry_date)


@router.message(MedicineUploadStates.entering_expiry_date, F.text)
async def process_expiry_date(message: Message, state: FSMContext):
    """Ввод срока годности"""
    try:
        date_str = message.text.strip()
        # Accept formats:
        # - DD.MM.YYYY  -> exact date
        # - MM.YYYY or MM.YY -> interpret as month/year; expiry becomes last day of PREVIOUS month
        expiry_date = None

        # Try full date first
        try:
            expiry_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        except Exception:
            # Try month.year (MM.YYYY or MM.YY)
            parts = date_str.split('.')
            if len(parts) == 2:
                month_part = parts[0]
                year_part = parts[1]
                try:
                    month = int(month_part)
                    year = int(year_part)
                    # If year is two digits, expand to 2000+YY (reasonable assumption)
                    if year < 100:
                        year += 2000
                    # Compute previous month
                    if month == 1:
                        prev_month = 12
                        prev_year = year - 1
                    else:
                        prev_month = month - 1
                        prev_year = year
                    # Last day of previous month
                    import calendar
                    last_day = calendar.monthrange(prev_year, prev_month)[1]
                    expiry_date = datetime(prev_year, prev_month, last_day).date()
                except Exception:
                    expiry_date = None

        if not expiry_date:
            raise ValueError("invalid date format")

        # Store as string to keep FSM storage serialization safe (Redis JSON)
        await state.update_data(item_expiry_date=expiry_date.strftime('%d.%m.%Y'))
        sent = await message.answer(
            LEXICON_RU['upload_enter_location'],
            reply_markup=get_skip_keyboard()
        )
        await _store_last_bot_message(state, sent_message=sent)
        await state.set_state(MedicineUploadStates.entering_location)

    except ValueError:
        try:
            await message.delete()
        except Exception:
            pass
        await _append_recommendation(state, message.bot, LEXICON_RU['recommend_invalid_date'])


@router.callback_query(MedicineUploadStates.entering_expiry_date, F.data == "skip")
async def skip_expiry_date(callback: CallbackQuery, state: FSMContext):
    """Пропуск срока годности"""
    await state.update_data(item_expiry_date=None)

    await callback.message.edit_text(
        LEXICON_RU['upload_enter_location'],
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MedicineUploadStates.entering_location)
    await callback.answer()


@router.message(MedicineUploadStates.entering_location, F.text)
async def process_location(message: Message, state: FSMContext):
    """Ввод местоположения"""
    location = message.text.strip()
    await state.update_data(item_location=location)

    sent = await message.answer(
        LEXICON_RU['upload_enter_item_notes'],
        reply_markup=get_skip_keyboard()
    )
    await _store_last_bot_message(state, sent_message=sent)
    await state.set_state(MedicineUploadStates.entering_item_notes)


@router.callback_query(MedicineUploadStates.entering_location, F.data == "skip")
async def skip_location(callback: CallbackQuery, state: FSMContext):
    """Пропуск местоположения"""
    await state.update_data(item_location=None)

    await callback.message.edit_text(
        LEXICON_RU['upload_enter_item_notes'],
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MedicineUploadStates.entering_item_notes)
    await callback.answer()


@router.message(MedicineUploadStates.entering_item_notes, F.text)
async def process_item_notes(message: Message, state: FSMContext):
    """Ввод заметок об экземпляре"""
    notes = message.text.strip()
    await state.update_data(item_notes=notes)

    # Показываем сводку
    await show_confirmation(message, state)


@router.callback_query(MedicineUploadStates.entering_item_notes, F.data == "skip")
async def skip_item_notes(callback: CallbackQuery, state: FSMContext):
    """Пропуск заметок об экземпляре"""
    await state.update_data(item_notes=None)

    # Показываем сводку
    await show_confirmation(callback.message, state)
    await callback.answer()


async def show_confirmation(message: Message, state: FSMContext):
    """Показать сводку и запросить подтверждение"""
    data = await state.get_data()

    # Восстанавливаем enum из строк для отображения
    medicine_type = MedicineType[data.get('medicine_type')] if data.get('medicine_type') else None
    medicine_category = MedicineCategory[data.get('medicine_category')] if data.get('medicine_category') else None

    # quantity уже строка, используем как есть
    expiry_val = data.get('item_expiry_date')
    if isinstance(expiry_val, str):
        expiry_display = expiry_val
    elif expiry_val:
        try:
            expiry_display = expiry_val.strftime('%d.%m.%Y')
        except Exception:
            expiry_display = str(expiry_val)
    else:
        expiry_display = '-'

    confirmation_text = LEXICON_RU['upload_confirm'].format(
        kit_name=data.get('kit_name', '-'),
        name=data.get('medicine_name', '-'),
        medicine_type=medicine_type.value if medicine_type else '-',
        category=medicine_category.value if medicine_category else '-',
        dosage=data.get('medicine_dosage') or '-',
        quantity=data.get('item_quantity', '-'),  # Это уже строка
        unit=data.get('item_unit', '-'),
        expiry_date=expiry_display,
        location=data.get('item_location') or '-',
        notes=data.get('item_notes') or '-'
    )

    await message.answer(confirmation_text, reply_markup=get_confirm_upload_medical_keyboard())
    await state.set_state(MedicineUploadStates.confirming)


@router.callback_query(MedicineUploadStates.confirming, F.data == "confirm_save")
async def save_medicine(
        callback: CallbackQuery,
        state: FSMContext,
        db_session: AsyncSession
):
    """Сохранение лекарства в базу данных"""
    data = await state.get_data()

    medicine_repo = MedicineRepository(db_session)
    item_repo = MedicineItemRepository(db_session)

    try:
        # Восстанавливаем enum из строк
        medicine_type = MedicineType[data['medicine_type']]
        medicine_category = MedicineCategory[data['medicine_category']]

        # Восстанавливаем Decimal из строки
        quantity = Decimal(data['item_quantity'])
        # Normalize expiry_date: stored as string in state, parse to date for DB
        expiry_raw = data.get('item_expiry_date')
        expiry_date_obj = None
        if expiry_raw:
            if isinstance(expiry_raw, str):
                try:
                    expiry_date_obj = datetime.strptime(expiry_raw, '%d.%m.%Y').date()
                except Exception:
                    expiry_date_obj = None
            else:
                expiry_date_obj = expiry_raw

        # Проверяем, используем ли существующее лекарство
        if data.get('using_existing_medicine') and data.get('selected_medicine_id'):
            medicine_id = data['selected_medicine_id']
        else:
            medicine = await medicine_repo.get_or_create(
                name=data['medicine_name'],
                medicine_type=medicine_type,
                category=medicine_category,
                dosage=data.get('medicine_dosage'),
                flags=0
            )

            # Обновляем заметки если они есть
            if data.get('medicine_notes'):
                await medicine_repo.update(
                    medicine.id,
                    notes=data['medicine_notes']
                )

            medicine_id = medicine.id

        # Создаем экземпляр в аптечке
        await item_repo.create(
            medicine_kit_id=data['medicine_kit_id'],
            medicine_id=medicine_id,
            quantity=quantity,  # Передаем Decimal в репозиторий
            unit=data['item_unit'],
            expiry_date=expiry_date_obj,
            location=data.get('item_location'),
            notes=data.get('item_notes')
        )

        await callback.message.edit_text(
            LEXICON_RU['upload_success'].format(
                name=data['medicine_name'],
                kit_name=data['kit_name']
            )
        )

        await state.clear()
        await callback.answer("✅ Сохранено!")

    except Exception as e:
        await callback.message.edit_text(LEXICON_RU['upload_error'])
        await callback.answer("❌ Ошибка", show_alert=True)
        logger.error(e)
        await state.clear()


@router.callback_query(StateFilter("*"), F.data == "cancel")
async def cancel_upload(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса добавления"""
    await callback.message.edit_text(LEXICON_RU['upload_cancelled'])
    await state.clear()
    await callback.answer()