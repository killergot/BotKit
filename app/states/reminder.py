from aiogram.fsm.state import State, StatesGroup


class ReminderCreateStates(StatesGroup):
    entering_text = State()
    entering_interval = State()
    choosing_type = State()


class ReminderEditStates(StatesGroup):
    choosing_field = State()
    entering_text = State()
    entering_interval = State()
