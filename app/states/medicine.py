from aiogram.fsm.state import State, StatesGroup


class MedicineUploadStates(StatesGroup):
    """Состояния для загрузки нового лекарства"""
    # Выбор/создание аптечки
    choosing_kit = State()

    # Данные о лекарстве (справочник)
    entering_name = State()
    choosing_type = State()
    choosing_category = State()
    entering_dosage = State()
    entering_medicine_notes = State()

    # Данные об экземпляре
    entering_quantity = State()
    entering_unit = State()
    entering_expiry_date = State()
    entering_location = State()
    entering_item_notes = State()

    # Подтверждение
    confirming = State()

class ShareKitStates(StatesGroup):
    """Состояния для шаринга аптечки"""
    choosing_kit = State()
    entering_username = State()
    confirming = State()