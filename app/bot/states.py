from aiogram.fsm.state import State, StatesGroup


class AddEventStates(StatesGroup):
    choosing_type = State()
    waiting_text = State()
    waiting_self_score = State()
