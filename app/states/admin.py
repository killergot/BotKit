from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    """Состояния для массовой рассылки администратора."""

    waiting_message = State()


class PrivateMessageStates(StatesGroup):
    """Состояния для отправки личных сообщений администратором."""

    choosing_user = State()
    waiting_message = State()

