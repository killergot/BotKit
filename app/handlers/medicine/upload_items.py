import decimal
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from rapidfuzz import fuzz, process

from app.database.models.medicine import MedicineType, MedicineCategory, Medicine
from app.keyboard.medicine_kb import (
    get_medicine_type_keyboard,
    get_medicine_category_keyboard,
    get_skip_keyboard,
    get_confirm_keyboard,
    get_medicine_kit_keyboard,
    get_similar_medicines_keyboard
)
from app.lexicon.lexicon import LEXICON_RU
from app.repositoryes.MedicineKitRepository import MedicineKitRepository
from app.repositoryes.MedicineRepository import MedicineRepository
from app.repositoryes.MedicineItemRepository import MedicineItemRepository
from app.states.medicine import MedicineUploadStates

router = Router()

# Минимальный процент совпадения для показа похожих лекарств
SIMILARITY_THRESHOLD = 60


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
        await message.answer(LEXICON_RU['upload_no_kits'])
        await state.set_state(MedicineUploadStates.choosing_kit)
        await state.update_data(creating_first_kit=True)
    else:
        # Показываем список аптечек
        await message.answer(
            LEXICON_RU['upload_start'],
            reply_markup=get_medicine_kit_keyboard(kits)
        )
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

    await message.answer(LEXICON_RU['upload_kit_created'].format(name=kit.name))

    # Сохраняем ID аптечки и переходим к вводу названия лекарства
    await state.update_data(medicine_kit_id=kit.id, kit_name=kit.name)
    await message.answer(LEXICON_RU['upload_enter_name'])
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

    await callback.message.edit_text(LEXICON_RU['upload_enter_name'])
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

    # Сохраняем введенное название
    await state.update_data(search_medicine_name=name)

    # Получаем все лекарства из базы
    medicine_repo = MedicineRepository(db_session)
    all_medicines = await medicine_repo.get_all()

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
                similar_text += f" - {med.medicine_type.value}, {med.category.value}\n"
                similar_text += f"   Совпадение: {score:.0f}%\n\n"

            similar_text += "Выберите подходящее или создайте новое:"

            # Извлекаем только объекты Medicine
            medicines_only = [med for med, _ in similar]

            await message.answer(
                similar_text,
                reply_markup=get_similar_medicines_keyboard(medicines_only)
            )
            return

    # Если похожих не найдено, продолжаем создание нового
    await state.update_data(medicine_name=name)
    await message.answer(
        LEXICON_RU['upload_choose_type'],
        reply_markup=get_medicine_type_keyboard()
    )
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
        reply_markup=get_medicine_type_keyboard()
    )
    await state.set_state(MedicineUploadStates.choosing_type)
    await callback.answer()


@router.callback_query(MedicineUploadStates.choosing_type, F.data.startswith("medicine_type:"))
async def process_medicine_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа лекарства"""
    type_name = callback.data.split(":")[1]
    medicine_type = MedicineType[type_name]

    await state.update_data(medicine_type=type_name)

    await callback.message.edit_text(
        LEXICON_RU['upload_choose_category'],
        reply_markup=get_medicine_category_keyboard()
    )
    await state.set_state(MedicineUploadStates.choosing_category)
    await callback.answer()


@router.callback_query(MedicineUploadStates.choosing_category, F.data.startswith("medicine_category:"))
async def process_medicine_category(callback: CallbackQuery, state: FSMContext):
    """Выбор категории лекарства"""
    category_name = callback.data.split(":")[1]
    category = MedicineCategory[category_name]

    await state.update_data(medicine_category=category_name)

    await callback.message.edit_text(
        LEXICON_RU['upload_enter_dosage'],
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MedicineUploadStates.entering_dosage)
    await callback.answer()


@router.message(MedicineUploadStates.entering_dosage, F.text)
async def process_dosage(message: Message, state: FSMContext):
    """Ввод дозировки"""
    dosage = message.text.strip()
    await state.update_data(medicine_dosage=dosage)

    await message.answer(
        LEXICON_RU['upload_enter_medicine_notes'],
        reply_markup=get_skip_keyboard()
    )
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

    await message.answer(LEXICON_RU['upload_enter_quantity'])
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

        # Сохраняем как строку!
        await state.update_data(item_quantity=str(quantity))
        await message.answer(LEXICON_RU['upload_enter_unit'])
        await state.set_state(MedicineUploadStates.entering_unit)

    except (ValueError, decimal.InvalidOperation):
        await message.answer(LEXICON_RU['error_invalid_number'])


@router.message(MedicineUploadStates.entering_unit, F.text)
async def process_unit(message: Message, state: FSMContext):
    """Ввод единицы измерения"""
    unit = message.text.strip()

    if not unit:
        await message.answer(LEXICON_RU['error_empty_input'])
        return

    await state.update_data(item_unit=unit)
    await message.answer(
        LEXICON_RU['upload_enter_expiry_date'],
        reply_markup=get_skip_keyboard()
    )
    await state.set_state(MedicineUploadStates.entering_expiry_date)


@router.message(MedicineUploadStates.entering_expiry_date, F.text)
async def process_expiry_date(message: Message, state: FSMContext):
    """Ввод срока годности"""
    try:
        date_str = message.text.strip()
        expiry_date = datetime.strptime(date_str, "%d.%m.%Y").date()

        await state.update_data(item_expiry_date=expiry_date)
        await message.answer(
            LEXICON_RU['upload_enter_location'],
            reply_markup=get_skip_keyboard()
        )
        await state.set_state(MedicineUploadStates.entering_location)

    except ValueError:
        await message.answer(LEXICON_RU['error_invalid_date'])


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

    await message.answer(
        LEXICON_RU['upload_enter_item_notes'],
        reply_markup=get_skip_keyboard()
    )
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
    confirmation_text = LEXICON_RU['upload_confirm'].format(
        kit_name=data.get('kit_name', '-'),
        name=data.get('medicine_name', '-'),
        medicine_type=medicine_type.value if medicine_type else '-',
        category=medicine_category.value if medicine_category else '-',
        dosage=data.get('medicine_dosage') or '-',
        quantity=data.get('item_quantity', '-'),  # Это уже строка
        unit=data.get('item_unit', '-'),
        expiry_date=data.get('item_expiry_date').strftime('%d.%m.%Y') if data.get('item_expiry_date') else '-',
        location=data.get('item_location') or '-',
        notes=data.get('item_notes') or '-'
    )

    await message.answer(confirmation_text, reply_markup=get_confirm_keyboard())
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

        # Проверяем, используем ли существующее лекарство
        if data.get('using_existing_medicine') and data.get('selected_medicine_id'):
            medicine_id = data['selected_medicine_id']
        else:
            # Создаем или получаем лекарство из справочника
            medicine = await medicine_repo.get_or_create(
                name=data['medicine_name'],
                medicine_type=medicine_type,
                category=medicine_category,
                dosage=data.get('medicine_dosage')
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
            expiry_date=data.get('item_expiry_date'),
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
        await state.clear()


@router.callback_query(StateFilter("*"), F.data == "cancel")
async def cancel_upload(callback: CallbackQuery, state: FSMContext):
    """Отмена процесса добавления"""
    await callback.message.edit_text(LEXICON_RU['upload_cancelled'])
    await state.clear()
    await callback.answer()